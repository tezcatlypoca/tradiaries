from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django import forms

from apps.core.models import UserPreferences
from apps.live_trading.views import DEFAULT_TRADING_SYMBOLS


class SignupForm(UserCreationForm):
    """Inscription libre : chaque compte démarre isolé, sans aucune donnée existante."""

    class Meta:
        model = get_user_model()
        fields = ('username',)


class UserStrategyForm(forms.ModelForm):
    """Formulaire de la stratégie générale + des actifs suivis (filtrage du bandeau news Vigil)."""

    tracked_assets = forms.MultipleChoiceField(
        choices=[(symbol, symbol) for symbol in DEFAULT_TRADING_SYMBOLS],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Actifs suivis',
        help_text="Utilisés pour filtrer les news affichées sur la page Trading (les news macro/géopolitiques générales restent toujours visibles).",
    )

    class Meta:
        model = UserPreferences
        fields = ('strategy',)
        widgets = {
            'strategy': forms.Textarea(
                attrs={
                    'rows': 8,
                    'placeholder': 'Décrivez votre stratégie de trading...',
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['tracked_assets'].initial = self.instance.tracked_assets

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.tracked_assets = self.cleaned_data.get('tracked_assets', [])
        if commit:
            instance.save()
        return instance
