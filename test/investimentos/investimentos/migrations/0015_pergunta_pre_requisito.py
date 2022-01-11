# Generated by Django 3.2.8 on 2022-01-06 22:07

from django.db import migrations
import django.db.models.deletion
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('investimentos', '0014_categoria_contabilizar'),
    ]

    operations = [
        migrations.AddField(
            model_name='pergunta',
            name='pre_requisito',
            field=sloth.db.models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='investimentos.pergunta', verbose_name='Pergunta'),
        ),
    ]