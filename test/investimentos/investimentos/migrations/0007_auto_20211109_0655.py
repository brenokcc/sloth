# Generated by Django 3.2.8 on 2021-11-09 06:55

from django.db import migrations, models
import django.db.models.deletion
import sloth.base
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('investimentos', '0006_auto_20211109_0557'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pergunta',
            name='tipo_resposta',
            field=models.IntegerField(choices=[[1, 'Texto Curto'], [2, 'Texto Longo'], [3, 'Número Decimal'], [4, 'Número Inteiro'], [5, 'Data']], verbose_name='Tipo de Resposta'),
        ),
        migrations.CreateModel(
            name='Questionario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('demanda', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.demanda', verbose_name='Demanda')),
            ],
            options={
                'verbose_name': 'Questionário',
                'verbose_name_plural': 'Questionários',
            },
            bases=(models.Model, sloth.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='PerguntaQuestionario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resposta', models.TextField(null=True, verbose_name='Resposta')),
                ('pergunta', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.pergunta', verbose_name='Pergunta')),
                ('questionario', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.demanda', verbose_name='Questionário')),
            ],
            options={
                'verbose_name': 'Resposta de Questionário',
                'verbose_name_plural': 'Respostas de Questionário',
            },
            bases=(models.Model, sloth.base.ModelMixin),
        ),
    ]
