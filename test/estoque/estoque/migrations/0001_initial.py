# Generated by Django 4.0.4 on 2022-04-16 17:54

from django.db import migrations, models
import sloth.core.base
import sloth.db.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Rede',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', sloth.db.models.CharField(max_length=255, verbose_name='Nome')),
            ],
            options={
                'verbose_name': 'Rede',
                'verbose_name_plural': 'Redes',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
    ]
