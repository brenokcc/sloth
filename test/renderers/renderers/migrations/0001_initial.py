# Generated by Django 4.1 on 2022-09-29 05:10

from django.db import migrations, models
import sloth.core.base


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Pessoa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
    ]
