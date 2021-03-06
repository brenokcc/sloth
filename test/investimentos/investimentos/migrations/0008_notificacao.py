# Generated by Django 3.2.8 on 2021-12-27 17:12

from django.db import migrations, models
import sloth.core.base
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('investimentos', '0007_alter_ciclo_teto'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notificacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', sloth.db.models.CharField(max_length=255, verbose_name='Descrição')),
                ('inicio', models.DateField(verbose_name='Início das Solicitações')),
                ('fim', models.DateField(verbose_name='Fim das Solicitações')),
            ],
            options={
                'verbose_name': 'Notificação',
                'verbose_name_plural': 'Notificações',
                'icon': 'exclamation-square',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
    ]
