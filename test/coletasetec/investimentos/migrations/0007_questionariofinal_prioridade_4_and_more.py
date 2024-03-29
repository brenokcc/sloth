# Generated by Django 4.1 on 2023-03-29 16:09

from django.db import migrations
import django.db.models.deletion
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('investimentos', '0006_categoria_cor'),
    ]

    operations = [
        migrations.AddField(
            model_name='questionariofinal',
            name='prioridade_4',
            field=sloth.db.models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='r4', to='investimentos.demanda', verbose_name='Prioridade 4'),
        ),
        migrations.AddField(
            model_name='questionariofinal',
            name='prioridade_5',
            field=sloth.db.models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='r5', to='investimentos.demanda', verbose_name='Prioridade 5'),
        ),
    ]
