"""Modèles Django pour persistance en BDD"""
from django.db import models
from django.utils import timezone

from .crypto import decrypt, encrypt


class Investment(models.Model):
    """Classe mère pour les investissements"""
    TRADE_MODES = [
        ('PAPER', 'Paper'),
        ('LIVE', 'Live'),
    ]

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
    notes = models.TextField(blank=True)
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
