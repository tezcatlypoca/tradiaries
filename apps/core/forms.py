from django import forms
from django.contrib import messages

from .models import ApiCredential, FuturesTrading, SimpleInvestment, SpotTrading


class SimpleInvestmentForm(forms.ModelForm):
    class Meta:
        model = SimpleInvestment
        fields = ('symbol', 'amount', 'price', 'action', 'notes')

    def clean_symbol(self):
        return self.cleaned_data['symbol'].strip().upper()

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('La quantité doit être strictement positive.')
        return amount

    def clean_price(self):
        price = self.cleaned_data['price']
        if price <= 0:
            raise forms.ValidationError('Le prix doit être strictement positif.')
        return price


class TradingForm(forms.ModelForm):
    class Meta:
        fields = (
            'symbol', 'amount', 'entry_price', 'exit_price', 'exit_price_2',
            'take_profit', 'stop_loss', 'notes'
        )

    def get_direction(self):
        """Sens du trade pour la validation TP/SL (spot = toujours LONG)."""
        return 'LONG'

    def clean_symbol(self):
        return self.cleaned_data['symbol'].strip().upper()

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('La quantité doit être strictement positive.')
        return amount

    def clean_entry_price(self):
        price = self.cleaned_data['entry_price']
        if price <= 0:
            raise forms.ValidationError("Le prix d'entrée doit être strictement positif.")
        return price

    def clean(self):
        cleaned_data = super().clean()
        exit_price = cleaned_data.get('exit_price')
        exit_price_2 = cleaned_data.get('exit_price_2')
        for field_name, price in (
            ('exit_price', exit_price), ('exit_price_2', exit_price_2)
        ):
            if price is not None and price <= 0:
                self.add_error(field_name, 'Le prix de sortie doit être strictement positif.')
        if exit_price_2 is not None and exit_price is None:
            self.add_error('exit_price', 'Le premier prix de sortie est requis avec une seconde sortie.')

        entry_price = cleaned_data.get('entry_price')
        take_profit = cleaned_data.get('take_profit')
        stop_loss = cleaned_data.get('stop_loss')
        for field_name, level in (('take_profit', take_profit), ('stop_loss', stop_loss)):
            if level is not None and level <= 0:
                self.add_error(field_name, 'Le niveau doit être strictement positif.')
        if entry_price:
            if self.get_direction() == 'SHORT':
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


class SpotTradingForm(TradingForm):
    class Meta(TradingForm.Meta):
        model = SpotTrading
        fields = TradingForm.Meta.fields + ('exchange', 'trade_mode')


class FuturesTradingForm(TradingForm):
    class Meta(TradingForm.Meta):
        model = FuturesTrading
        fields = TradingForm.Meta.fields + (
            'direction', 'risk_reward_ratio', 'feeling', 'why', 'strategy', 'trade_mode'
        )

    def get_direction(self):
        return self.cleaned_data.get('direction') or 'LONG'

    def clean_risk_reward_ratio(self):
        ratio = self.cleaned_data.get('risk_reward_ratio')
        if ratio is not None and ratio <= 0:
            raise forms.ValidationError('Le ratio risque/rendement doit être positif.')
        return ratio


def add_form_errors_to_messages(request, form):
    for field_errors in form.errors.values():
        for error in field_errors:
            messages.error(request, error)


class ApiCredentialForm(forms.Form):
    """Formulaire d'ajout de clé API : les champs requis dépendent de la plateforme choisie."""
    platform = forms.ChoiceField(choices=ApiCredential.PLATFORMS)
    label = forms.CharField(max_length=50, required=False)
    api_key = forms.CharField(max_length=255)
    api_secret = forms.CharField(max_length=255, required=False)
    passphrase = forms.CharField(max_length=255, required=False)

    def clean(self):
        cleaned_data = super().clean()
        platform = cleaned_data.get('platform')
        requirements = ApiCredential.PLATFORM_REQUIREMENTS.get(platform, {})
        if requirements.get('secret') and not cleaned_data.get('api_secret'):
            self.add_error('api_secret', 'La clé secrète est requise pour cette plateforme.')
        if requirements.get('passphrase') and not cleaned_data.get('passphrase'):
            self.add_error('passphrase', 'La passphrase est requise pour cette plateforme.')
        # Une seule clé active par plateforme : Kraken (et les autres) ne choisissent
        # jamais silencieusement "la première" en cas de doublon.
        if platform and ApiCredential.objects.filter(platform=platform).exists():
            self.add_error(
                'platform',
                'Une clé existe déjà pour cette plateforme. Supprimez-la avant d\'en ajouter une nouvelle.',
            )
        return cleaned_data