# Generated by Django 4.1 on 2023-03-29 07:29

from django.db import migrations
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('investimentos', '0005_remove_administrador_user_remove_demanda_ciclo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoria',
            name='cor',
            field=sloth.db.models.ColorField(default='#FFFFFF', max_length=7, verbose_name='Cor'),
        ),
    ]
