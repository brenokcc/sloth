# Generated by Django 3.2.8 on 2022-03-19 10:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('investimentos', '0023_remove_administrador_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gestor',
            name='user',
        ),
    ]
