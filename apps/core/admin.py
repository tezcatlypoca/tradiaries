from django.contrib import admin

from .models import ApiCredential, FuturesTrading, KrakenOrderAttempt, SimpleInvestment, SpotTrading


@admin.register(SimpleInvestment)
class SimpleInvestmentAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'user', 'action', 'amount', 'price', 'entry_date', 'external_ref')
    list_filter = ('user', 'action', 'entry_date')
    search_fields = ('symbol', 'external_ref', 'notes')


@admin.register(SpotTrading)
class SpotTradingAdmin(admin.ModelAdmin):
    list_display = (
        'symbol', 'user', 'exchange', 'trade_mode', 'amount', 'entry_price', 'exit_price',
        'take_profit', 'stop_loss', 'external_ref', 'entry_date'
    )
    list_filter = ('user', 'exchange', 'trade_mode', 'entry_date')
    search_fields = ('symbol', 'external_ref', 'notes')


@admin.register(FuturesTrading)
class FuturesTradingAdmin(admin.ModelAdmin):
    list_display = (
        'symbol', 'user', 'direction', 'trade_mode', 'strategy', 'amount',
        'entry_price', 'exit_price', 'take_profit', 'stop_loss', 'external_ref', 'entry_date'
    )
    list_filter = ('user', 'direction', 'trade_mode', 'feeling', 'strategy', 'entry_date')
    search_fields = ('symbol', 'external_ref', 'strategy', 'why', 'notes')


@admin.register(ApiCredential)
class ApiCredentialAdmin(admin.ModelAdmin):
    # Les clés API se gèrent depuis la page Paramètres (chiffrement transparent) ; l'admin est en lecture seule.
    list_display = ('platform', 'label', 'created_at', 'updated_at')
    list_filter = ('platform',)
    search_fields = ('label',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(KrakenOrderAttempt)
class KrakenOrderAttemptAdmin(admin.ModelAdmin):
    # Journal de réconciliation des ordres LIVE : lecture seule, ne se crée/modifie que via trading_service.
    list_display = (
        'created_at', 'operation', 'symbol', 'side', 'volume', 'status',
        'external_ref', 'kraken_userref', 'spot_trade',
    )
    list_filter = ('status', 'operation', 'symbol')
    search_fields = ('client_order_id', 'external_ref', 'error_message')
    readonly_fields = [f.name for f in KrakenOrderAttempt._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False