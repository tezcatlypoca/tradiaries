from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django import forms

from apps.core.models import UserPreferences


class SignupForm(UserCreationForm):
    """Inscription libre : chaque compte démarre isolé, sans aucune donnée existante."""

    class Meta:
        model = get_user_model()
        fields = ('username',)


class UserStrategyForm(forms.ModelForm):
    """Formulaire de la stratégie générale définie par l'utilisateur."""

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
