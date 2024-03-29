# Generated by Django 4.1 on 2022-09-22 14:51

from django.db import migrations, models
import django.db.models.deletion
import sloth.core.base
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_alter_application_client_secret'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('secret', sloth.db.models.CharField(max_length=16, verbose_name='Chave')),
                ('user', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.user', verbose_name='Usuário')),
                ('active', models.BooleanField(default=False, verbose_name='Ativo'))
            ],
            options={
                'verbose_name': 'Código de Autenticação',
                'verbose_name_plural': 'Códigos de Autenticação',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        )
    ]
