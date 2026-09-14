"""Migration de données : rattache toutes les données existantes au compte superuser existant.

L'app était mono-utilisateur jusqu'ici (un seul compte créé via createsuperuser) ;
cette migration attribue explicitement l'historique à ce compte avant de rendre
le champ `user` obligatoire (migration suivante).
"""
from django.db import migrations


def assign_existing_data_to_first_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    owner = User.objects.filter(is_superuser=True).order_by('id').first() or User.objects.order_by('id').first()
    if owner is None:
        # Aucun compte existant (base neuve) : rien à rattacher.
        return

    for model_name in ('SimpleInvestment', 'SpotTrading', 'FuturesTrading', 'ApiCredential', 'KrakenOrderAttempt'):
        Model = apps.get_model('core', model_name)
        Model.objects.filter(user__isnull=True).update(user=owner)

    KrakenNonceCounter = apps.get_model('core', 'KrakenNonceCounter')
    # Ancien singleton (pk=1) : devient le compteur de l'unique compte existant.
    KrakenNonceCounter.objects.filter(user__isnull=True).update(user=owner)


def noop_reverse(apps, schema_editor):
    """Rien à défaire : on ne retire pas le rattachement d'un propriétaire déjà en place."""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_add_user_ownership_nullable'),
    ]

    operations = [
        migrations.RunPython(assign_existing_data_to_first_superuser, noop_reverse),
    ]
