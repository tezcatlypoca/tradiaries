from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class SignupForm(UserCreationForm):
    """Inscription libre : chaque compte démarre isolé, sans aucune donnée existante."""

    class Meta:
        model = get_user_model()
        fields = ('username',)
