# Generated by Django 3.2.8 on 2022-01-20 18:12

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('investimentos', '0020_auto_20220119_0656'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mensagem',
            name='notificados',
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, verbose_name='Notificados'),
        ),
    ]