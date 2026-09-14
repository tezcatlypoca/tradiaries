# Generated manually: makes `user` mandatory now that 0013 has backfilled existing rows.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_backfill_user_ownership'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apicredential',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='api_credentials', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='futurestrading',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_set', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='krakennoncecounter',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='kraken_nonce_counter', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='krakenorderattempt',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kraken_order_attempts', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='simpleinvestment',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='simple_investments', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='spottrading',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_set', to=settings.AUTH_USER_MODEL),
        ),
    ]
