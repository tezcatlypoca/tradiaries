"""Modèles Django pour persistance en BDD"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from .crypto import decrypt, encrypt


class Investment(models.Model):
    """Classe mère pour les investissements"""
    TRADE_MODES = [
        ('PAPER', 'Paper'),
        ('LIVE', 'Live'),
    ]

    # Propriétaire de la position : chaque utilisateur ne voit/gère que ses propres données.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='%(class)s_set')
    symbol = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=15, decimal_places=8)
    entry_price = models.DecimalField(max_digits=15, decimal_places=8)
    exit_price = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    exit_price_2 = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    # Take profit / stop loss optionnels, surveillés par l'app (commande watch_tp_sl)
    take_profit = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    # txid de l'ordre Kraken d'ouverture (positions ouvertes depuis la page Trading Live)
    external_ref = models.CharField(max_length=64, unique=True, null=True, blank=True)
    entry_date = models.DateTimeField(default=timezone.now)
    # Unité de temps du graphique utilisée pour la décision de trade (texte libre, ex: "15min", "4h", "1D")
    timeframe = models.CharField(max_length=20, blank=True, help_text="Time frame utilisé (ex: 15min, 1h, 4h, 1D)")
    notes = models.TextField(blank=True)
    # Verrou anti double-clôture (watcher + clic manuel concurrents) : revendiqué
    # atomiquement par trading_service.close_position() avant tout appel Kraken.
    is_closing = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def effective_exit_price(self):
        """Return the average exit price when two equal-sized exits are recorded."""
        if self.exit_price is None:
            return None
        if self.exit_price_2 is None:
            return self.exit_price
        return (self.exit_price + self.exit_price_2) / 2


class SimpleInvestment(models.Model):
    """Investissement simple : un achat ou une vente unique"""
    ACTIONS = [
        ('ACHAT', 'Achat'),
        ('VENTE', 'Vente'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='simple_investments')
    symbol = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=15, decimal_places=8)
    price = models.DecimalField(max_digits=15, decimal_places=8)
    action = models.CharField(max_length=5, choices=ACTIONS, default='ACHAT')
    entry_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    # Identifiant Kraken (txid) pour éviter les doublons lors de l'import automatique
    external_ref = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        date_str = self.entry_date.date() if self.entry_date else "N/A"
        return f"{self.symbol} ({date_str})"

    class Meta:
        db_table = 'core_simple_investment'
        verbose_name = 'Simple Investment'
        verbose_name_plural = 'Simple Investments'


class SpotTrading(Investment):
    """Trading spot sur échange"""
    EXCHANGES = [
        ('BINANCE', 'Binance'),
        ('KRAKEN', 'Kraken'),
        ('COINBASE', 'Coinbase'),
        ('OTHER', 'Autre'),
    ]
    exchange = models.CharField(max_length=20, choices=EXCHANGES, default='BINANCE')
    trade_mode = models.CharField(
        max_length=5, choices=Investment.TRADE_MODES, default='PAPER',
        help_text="Position réelle (Live) ou fictive (Paper)",
    )

    class Meta:
        db_table = 'core_spot_trading'
        verbose_name = 'Spot Trading'
        verbose_name_plural = 'Spot Tradings'

    def __str__(self):
        date_str = self.entry_date.date() if self.entry_date else "N/A"
        return f"{self.symbol} - {self.exchange} ({date_str})"


class FuturesTrading(Investment):
    """Trading futures avec effet de levier"""
    DIRECTIONS = [
        ('LONG', 'Long'),
        ('SHORT', 'Short'),
    ]
    FEELINGS = [
        ('VERY_BULLISH', 'Très haussier'),
        ('BULLISH', 'Haussier'),
        ('NEUTRAL', 'Neutre'),
        ('BEARISH', 'Baissier'),
        ('VERY_BEARISH', 'Très baissier'),
    ]

    direction = models.CharField(max_length=5, choices=DIRECTIONS, default='LONG')
    risk_reward_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    feeling = models.CharField(max_length=20, choices=FEELINGS, blank=True)
    why = models.TextField(blank=True, help_text="Raison de la prise de position")
    strategy = models.CharField(max_length=50, blank=True, help_text="Nom de la stratégie utilisée (ex: IRC 4h, VP 15min)")
    trade_mode = models.CharField(
        max_length=5, choices=Investment.TRADE_MODES, default='PAPER',
        help_text="Position réelle (Live) ou fictive (Paper)",
    )

    class Meta:
        db_table = 'core_futures_trading'
        verbose_name = 'Futures Trading'
        verbose_name_plural = 'Futures Tradings'

    def __str__(self):
        date_str = self.entry_date.date() if self.entry_date else "N/A"
        return f"{self.symbol} {self.direction} ({date_str})"


class KrakenOrderAttempt(models.Model):
    """Trace persistée de chaque tentative d'ordre Kraken LIVE, créée AVANT l'appel réseau.

    Garantit qu'un identifiant client et un état survivent même si le processus
    plante entre l'acceptation de l'ordre par Kraken et l'écriture locale de la
    position (SpotTrading) : la ligne reste consultable (admin) pour réconciliation
    manuelle au lieu de disparaître silencieusement.
    """
    OPERATIONS = [
        ('OPEN', 'Ouverture'),
        ('CLOSE', 'Clôture'),
    ]
    STATUSES = [
        ('PENDING', "En attente d'envoi"),
        ('SUBMITTED', 'Soumis à Kraken'),
        ('CONFIRMED', 'Confirmé (position à jour)'),
        ('FAILED', 'Échec avant confirmation Kraken'),
        ('RECONCILE_REQUIRED', 'Réconciliation manuelle requise'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kraken_order_attempts')
    client_order_id = models.CharField(max_length=32, unique=True)
    kraken_userref = models.BigIntegerField(null=True, blank=True)
    operation = models.CharField(max_length=5, choices=OPERATIONS)
    symbol = models.CharField(max_length=20)
    side = models.CharField(max_length=4)
    volume = models.DecimalField(max_digits=15, decimal_places=8)
    status = models.CharField(max_length=20, choices=STATUSES, default='PENDING')
    external_ref = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    spot_trade = models.ForeignKey(
        SpotTrading, null=True, blank=True, on_delete=models.SET_NULL, related_name='kraken_attempts',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_kraken_order_attempt'
        verbose_name = 'Tentative ordre Kraken'
        verbose_name_plural = 'Tentatives ordres Kraken'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.operation} {self.symbol} [{self.status}]"


class KrakenNonceCounter(models.Model):
    """Singleton (pk=1) : compteur monotone partagé entre process/threads pour le nonce Kraken.

    Un nonce basé uniquement sur l'horloge peut entrer en collision ou régresser
    entre deux workers Gunicorn/le watcher exécutés en parallèle. Ce compteur,
    incrémenté sous verrou DB (select_for_update), garantit un nonce strictement
    croissant quel que soit le nombre de processus.

    Un compteur par utilisateur : chaque compte utilise ses propres clés Kraken,
    donc son propre espace de nonce (un nonce est spécifique à une paire clé/secret).
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kraken_nonce_counter')
    value = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'core_kraken_nonce_counter'


class ApiCredential(models.Model):
    """Clé API d'une plateforme externe (échange ou fournisseur de données), stockée chiffrée."""
    PLATFORMS = [
        ('KRAKEN', 'Kraken'),
        ('BINANCE', 'Binance'),
        ('BITGET', 'Bitget'),
        ('COINMARKETCAP', 'CoinMarketCap'),
        ('OTHER', 'Autre'),
    ]
    # Champs requis en plus de api_key selon la plateforme (utilisé par ApiCredentialForm et le JS du formulaire)
    PLATFORM_REQUIREMENTS = {
        'KRAKEN': {'secret': True, 'passphrase': False},
        'BINANCE': {'secret': True, 'passphrase': False},
        'BITGET': {'secret': True, 'passphrase': True},
        'COINMARKETCAP': {'secret': False, 'passphrase': False},
        'OTHER': {'secret': False, 'passphrase': False},
    }

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='api_credentials')
    platform = models.CharField(max_length=20, choices=PLATFORMS)
    label = models.CharField(max_length=50, blank=True, help_text="Nom libre pour distinguer plusieurs clés d'une même plateforme")
    api_key = models.TextField(help_text="Chiffré en BDD")
    api_secret = models.TextField(blank=True, help_text="Chiffré en BDD")
    passphrase = models.TextField(blank=True, help_text="Chiffré en BDD")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_api_credential'
        verbose_name = 'Clé API'
        verbose_name_plural = 'Clés API'
        ordering = ['platform', 'label']

    def __str__(self):
        return f"{self.get_platform_display()}" + (f" ({self.label})" if self.label else "")

    def set_credentials(self, api_key: str = '', api_secret: str = '', passphrase: str = '') -> None:
        """Chiffre et affecte les secrets fournis en clair."""
        self.api_key = encrypt(api_key)
        self.api_secret = encrypt(api_secret)
        self.passphrase = encrypt(passphrase)

    def get_api_key(self) -> str:
        return decrypt(self.api_key)

    def get_api_secret(self) -> str:
        return decrypt(self.api_secret)

    def get_passphrase(self) -> str:
        return decrypt(self.passphrase)

    def masked_api_key(self) -> str:
        """Affiche uniquement les 4 derniers caractères de la clé, pour vérification visuelle sans exposer le secret."""
        plain = self.get_api_key()
        if len(plain) <= 4:
            return '••••'
        return f"{'•' * (len(plain) - 4)}{plain[-4:]}"


class UserPreferences(models.Model):
    """Préférences de trading propres à un utilisateur."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tradiaries_preferences',
    )
    strategy = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_user_preferences'
        verbose_name = 'Préférences utilisateur'
        verbose_name_plural = 'Préférences utilisateur'

    def __str__(self) -> str:
        return f"Préférences de {self.user}"


class WatcherHeartbeat(models.Model):
    """Ligne unique (pk=1) : instant du dernier cycle réussi du watcher TP/SL.

    Stocké en BDD plutôt que sur disque local : le watcher (ex. worker Railway)
    et le serveur web qui expose /healthz/watcher/ (ex. Render) n'ont pas
    forcément de système de fichiers commun, mais partagent toujours la même BDD.
    """
    last_heartbeat = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'core_watcher_heartbeat'
