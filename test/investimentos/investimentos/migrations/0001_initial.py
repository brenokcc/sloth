# Generated by Django 3.2.8 on 2021-11-20 09:20

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import sloth.core.base
import sloth.db.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Ano',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ano', models.IntegerField(verbose_name='Ano')),
            ],
            options={
                'verbose_name': 'Ano',
                'verbose_name_plural': 'Anos',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Campus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', sloth.db.models.CharField(max_length=255, verbose_name='Nome')),
                ('sigla', sloth.db.models.CharField(max_length=255, verbose_name='Sigla')),
            ],
            options={
                'verbose_name': 'Campus',
                'verbose_name_plural': 'Campi',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', sloth.db.models.CharField(max_length=255, verbose_name='Nome')),
            ],
            options={
                'verbose_name': 'Categoria de Investimento',
                'verbose_name_plural': 'Categorias de Investimento',
                'icon': 'folder',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Ciclo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', sloth.db.models.CharField(max_length=255, verbose_name='Descrição')),
                ('inicio', models.DateField(verbose_name='Início das Solicitações')),
                ('fim', models.DateField(verbose_name='Fim das Solicitações')),
                ('teto', sloth.db.models.DecimalField(decimal_places=2, max_digits=9, verbose_name='Limite Orçamentário (R$)')),
            ],
            options={
                'verbose_name': 'Ciclo de Solicitação de Investimento',
                'verbose_name_plural': 'Ciclos de Solicitação de Investimento',
                'icon': 'arrow-clockwise',
                'fieldsets': {'Dados Gerais': ('descricao', 'instituicoes'), 'Limite Financeiro': ('teto',), 'Período de Solicitação': (('inicio', 'fim'),)},
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Demanda',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.TextField(verbose_name='Descrição')),
                ('valor', sloth.db.models.DecimalField(decimal_places=2, max_digits=9, null=True, verbose_name='Valor a Empenhar no Exercício (R$)')),
                ('finalizada', models.BooleanField(default=False, verbose_name='Finalizada')),
                ('ciclo', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.ciclo', verbose_name='Ciclo')),
                ('classificacao', sloth.db.models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='investimentos.categoria', verbose_name='Classificação')),
            ],
            options={
                'verbose_name': 'Demanda',
                'verbose_name_plural': 'Demandas',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Instituicao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', sloth.db.models.CharField(max_length=255, verbose_name='Nome')),
                ('sigla', sloth.db.models.CharField(max_length=255, verbose_name='Sigla')),
            ],
            options={
                'verbose_name': 'Instituição',
                'verbose_name_plural': 'Instituições',
                'icon': 'building',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='OpcaoResposta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', sloth.db.models.CharField(max_length=255, verbose_name='Resposta')),
            ],
            options={
                'verbose_name': 'Opção de Resposta',
                'verbose_name_plural': 'Opções de Resposta',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Pergunta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texto', sloth.db.models.CharField(max_length=255, verbose_name='Texto')),
                ('obrigatoria', models.BooleanField(blank=True, verbose_name='Obrigatória')),
                ('tipo_resposta', models.IntegerField(choices=[[1, 'Texto Curto'], [2, 'Texto Longo'], [3, 'Valor Monetário'], [4, 'Número Inteiro'], [5, 'Data'], [6, 'Sim/Não'], [7, 'Arquivo'], [8, 'Múltiplas Escolhas']], verbose_name='Tipo de Resposta')),
                ('categoria', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.categoria', verbose_name='Categoria')),
                ('opcoes', sloth.db.models.OneToManyField(blank=True, to='investimentos.OpcaoResposta', verbose_name='Opções de Resposta')),
            ],
            options={
                'verbose_name': 'Pergunta',
                'verbose_name_plural': 'Perguntas',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Prioridade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.IntegerField(verbose_name='Número')),
            ],
            options={
                'verbose_name': 'Prioridade',
                'verbose_name_plural': 'Prioridades',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
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
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='RespostaQuestionario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resposta', models.TextField(null=True, verbose_name='Resposta')),
                ('pergunta', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.pergunta', verbose_name='Pergunta')),
                ('questionario', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.questionario', verbose_name='Questionário')),
            ],
            options={
                'verbose_name': 'Resposta de Questionário',
                'verbose_name_plural': 'Respostas dos Questionários',
                'icon': 'pencil-square',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='LimiteDemanda',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantidade', models.PositiveIntegerField(verbose_name='Quantidade Máxima de Demandas')),
                ('classificacao', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.categoria', verbose_name='Classificação')),
            ],
            options={
                'verbose_name': 'Limite de Demanda',
                'verbose_name_plural': 'Limites de Demanda',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Gestor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', sloth.db.models.CharField(max_length=255, verbose_name='Nome')),
                ('cpf', sloth.db.models.CharField(max_length=255, verbose_name='CPF')),
                ('instituicao', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.instituicao', verbose_name='Instituição')),
                ('user', sloth.db.models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Usuário')),
            ],
            options={
                'verbose_name': 'Gestor ',
                'verbose_name_plural': 'Gestores',
                'fieldsets': {'Dados Gerais': (('nome', 'cpf'), 'instituicao')},
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.AddField(
            model_name='demanda',
            name='instituicao',
            field=sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.instituicao', verbose_name='Instituição'),
        ),
        migrations.AddField(
            model_name='demanda',
            name='prioridade',
            field=sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.prioridade', verbose_name='Prioridade'),
        ),
        migrations.AddField(
            model_name='demanda',
            name='unidades_beneficiadas',
            field=models.ManyToManyField(blank=True, help_text='Não informar caso todas as unidades sejam beneficiadas.', to='investimentos.Campus', verbose_name='Unidades Beneficiadas'),
        ),
        migrations.AddField(
            model_name='ciclo',
            name='instituicoes',
            field=models.ManyToManyField(blank=True, help_text='Não informar, caso deseje incluir todas as instituições.', to='investimentos.Instituicao', verbose_name='Demandantes'),
        ),
        migrations.AddField(
            model_name='ciclo',
            name='limites',
            field=sloth.db.models.OneToManyField(to='investimentos.LimiteDemanda', verbose_name='Limites de Demanda'),
        ),
        migrations.AddField(
            model_name='campus',
            name='instituicao',
            field=sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='investimentos.instituicao', verbose_name='Campus'),
        ),
        migrations.CreateModel(
            name='Administrador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', sloth.db.models.CharField(max_length=255, verbose_name='Nome')),
                ('cpf', sloth.db.models.CharField(max_length=255, verbose_name='CPF')),
                ('user', sloth.db.models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Usuário')),
            ],
            options={
                'verbose_name': 'Administrador',
                'verbose_name_plural': 'Administradores',
                'icon': 'person-workspace',
                'fieldsets': {'Dados Gerais': ('nome', 'cpf')},
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
    ]
