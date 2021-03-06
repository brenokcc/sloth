# Generated by Django 4.0.4 on 2022-04-23 14:32

from django.db import migrations, models
import sloth.core.base
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('petshop', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Administrador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', sloth.db.models.CharField(max_length=255, verbose_name='None')),
                ('cpf', sloth.db.models.CharField(max_length=255, verbose_name='CPF')),
            ],
            options={
                'verbose_name': 'Administrador',
                'verbose_name_plural': 'Administrador',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
    ]
