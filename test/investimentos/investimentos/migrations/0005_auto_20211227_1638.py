# Generated by Django 3.2.8 on 2021-12-27 16:38

from django.db import migrations, models
import sloth.core.base
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('investimentos', '0004_questionariofinal_finalizado'),
    ]

    operations = [
        migrations.CreateModel(
            name='Anexo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', sloth.db.models.CharField(max_length=255, verbose_name='Descrição')),
                ('arquivo', models.FileField(upload_to='anexos', verbose_name='Arquivo')),
            ],
            options={
                'verbose_name': 'Anexo',
                'verbose_name_plural': 'Anexos',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.AlterModelOptions(
            name='questionariofinal',
            options={'verbose_name': 'Questionário Final', 'verbose_name_plural': 'Questionários Finais'},
        ),
        migrations.AddField(
            model_name='mensagem',
            name='anexos',
            field=sloth.db.models.OneToManyField(to='investimentos.Anexo', verbose_name='Anexos'),
        ),
    ]
