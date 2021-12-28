# Generated by Django 3.2.8 on 2021-12-28 16:35

from django.db import migrations
import django.db.models.deletion
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('investimentos', '0011_auto_20211228_1620'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='duvida',
            options={'verbose_name': 'Dúvida', 'verbose_name_plural': 'Dúvidas'},
        ),
        migrations.AddField(
            model_name='duvida',
            name='instituicao',
            field=sloth.db.models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='investimentos.instituicao', verbose_name='Instituicao'),
        ),
    ]
