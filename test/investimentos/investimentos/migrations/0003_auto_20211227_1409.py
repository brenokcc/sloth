# Generated by Django 3.2.8 on 2021-12-27 14:09

from django.db import migrations, models
import django.db.models.deletion
import sloth.core.base
import sloth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('investimentos', '0002_mensagem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='demanda',
            name='classificacao',
            field=sloth.db.models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='investimentos.categoria', verbose_name='Categoria'),
        ),
        migrations.AlterField(
            model_name='demanda',
            name='descricao',
            field=sloth.db.models.CharField(max_length=512, verbose_name='Descrição'),
        ),
        migrations.CreateModel(
            name='QuestionarioFinal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rco_pendente', sloth.db.models.CharField(choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']], max_length=255, verbose_name='RCO Pendente')),
                ('detalhe_rco_pendente', models.TextField(blank=True, null=True, verbose_name='Detalhe de RCO Pendente')),
                ('devolucao_ted', sloth.db.models.CharField(choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']], max_length=255, verbose_name='Devolução de TED')),
                ('detalhe_devolucao_ted', models.TextField(blank=True, null=True, verbose_name='Detalhe de Devolução de TED')),
                ('ciclo', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.ciclo', verbose_name='Ciclo')),
                ('instituicao', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.instituicao', verbose_name='Instituição')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
    ]
