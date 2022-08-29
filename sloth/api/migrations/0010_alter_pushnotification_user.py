# Generated by Django 4.0.4 on 2022-08-08 20:11

from django.conf import settings
from django.db import migrations
import django.db.models.deletion
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0009_pushnotification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pushnotification',
            name='user',
            field=sloth.db.models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='push_notification', to=settings.AUTH_USER_MODEL, verbose_name='Usuário'),
        ),
    ]