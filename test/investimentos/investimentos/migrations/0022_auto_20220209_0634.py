# Generated by Django 3.2.8 on 2022-02-09 06:34

from django.db import migrations
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('investimentos', '0021_alter_mensagem_notificados'),
    ]

    operations = [
        migrations.AlterField(
            model_name='demanda',
            name='valor',
            field=sloth.db.models.DecimalField(decimal_places=2, max_digits=15, null=True, verbose_name='Valor a Empenhar no Exercício (R$)'),
        ),
        migrations.AlterField(
            model_name='demanda',
            name='valor_total',
            field=sloth.db.models.DecimalField(decimal_places=2, max_digits=15, null=True, verbose_name='Valor Total (R$)'),
        ),
    ]
