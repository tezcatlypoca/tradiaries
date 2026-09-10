"""Formulaire d'ouverture de position (spot/futures, paper/live) de la page Trading Live."""
from decimal import Decimal

from django import forms

from apps.core.models import FuturesTrading, Investment


class OpenPositionForm(forms.Form):
    """Valide les paramètres d'une nouvelle position (les deux modèles partagent les règles)."""

    CATEGORIES = [('SPOT', 'Spot'), ('FUTURES', 'Futures')]

    category = forms.ChoiceField(choices=CATEGORIES)
    trade_mode = forms.ChoiceField(choices=Investment.TRADE_MODES)
    symbol = forms.CharField(max_length=20)
    amount = forms.DecimalField(min_value=Decimal('0.00000001'), max_digits=15, decimal_places=8)
    # Prix d'entrée vide = entrée au prix du marché
    entry_price = forms.DecimalField(
        required=False, min_value=Decimal('0.00000001'), max_digits=15, decimal_places=8
    )
    direction = forms.ChoiceField(choices=FuturesTrading.DIRECTIONS, required=False)
    take_profit = forms.DecimalField(
        required=False, min_value=Decimal('0.00000001'), max_digits=15, decimal_places=8
    )
    stop_loss = forms.DecimalField(
        required=False, min_value=Decimal('0.00000001'), max_digits=15, decimal_places=8
    )
    strategy = forms.CharField(max_length=50, required=False)
    feeling = forms.ChoiceField(
        choices=[('', '-')] + FuturesTrading.FEELINGS, required=False
    )
    why = forms.CharField(required=False)
    notes = forms.CharField(required=False)
    regime_confirmed = forms.BooleanField(required=False)
    sar_confirmed = forms.BooleanField(required=False)
    volume_profile_confirmed = forms.BooleanField(required=False)

    def clean_symbol(self):
        return self.cleaned_data['symbol'].strip().upper()

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        trade_mode = cleaned_data.get('trade_mode')
        direction = cleaned_data.get('direction')
        entry_price = cleaned_data.get('entry_price')
        take_profit = cleaned_data.get('take_profit')
        stop_loss = cleaned_data.get('stop_loss')

        if category == 'FUTURES' and not direction:
            self.add_error('direction', 'La direction est requise pour une position futures.')

        if trade_mode == 'LIVE':
            validated_criteria = sum(
                cleaned_data.get(field_name, False)
                for field_name in (
                    'regime_confirmed',
                    'sar_confirmed',
                    'volume_profile_confirmed',
                )
            )
            if validated_criteria < 2:
                raise forms.ValidationError(
                    'Ordre LIVE refusé : validez au moins 2 des 3 critères de la stratégie IRC.'
                )

        # Cohérence TP/SL par rapport au sens du trade (spot = toujours LONG).
        # Vérifiable uniquement si un prix d'entrée explicite est fourni.
        if entry_price is None or (take_profit is None and stop_loss is None):
            return cleaned_data

        effective_direction = direction if category == 'FUTURES' else 'LONG'
        if effective_direction == 'SHORT':
            if take_profit is not None and take_profit >= entry_price:
                self.add_error('take_profit', "En SHORT, le TP doit être sous le prix d'entrée.")
            if stop_loss is not None and stop_loss <= entry_price:
                self.add_error('stop_loss', "En SHORT, le SL doit être au-dessus du prix d'entrée.")
        else:
            if take_profit is not None and take_profit <= entry_price:
                self.add_error('take_profit', "En LONG, le TP doit être au-dessus du prix d'entrée.")
            if stop_loss is not None and stop_loss >= entry_price:
                self.add_error('stop_loss', "En LONG, le SL doit être sous le prix d'entrée.")
        return cleaned_data
