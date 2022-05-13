# Generated by Django 3.2.8 on 2021-11-09 06:17

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
            name='Endereco',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('logradouro', sloth.db.models.CharField(max_length=255, verbose_name='Logradouro')),
                ('numero', sloth.db.models.CharField(max_length=255, verbose_name='Número')),
            ],
            options={
                'verbose_name': 'Endereço',
                'verbose_name_plural': 'Endereços',
                'fieldsets': {'Dados Gerais': ('logradouro', ('numero', 'municipio'))},
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Estado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sigla', sloth.db.models.CharField(max_length=255, verbose_name='Sigla')),
            ],
            options={
                'verbose_name': 'Estado',
                'verbose_name_plural': 'Estados',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Instituto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sigla', sloth.db.models.CharField(max_length=255, verbose_name='Sigla')),
            ],
            options={
                'verbose_name': 'Instituto',
                'verbose_name_plural': 'Instituto',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Municipio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', sloth.db.models.CharField(max_length=255, verbose_name='Nome')),
                ('estado', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.estado', verbose_name='Estado')),
            ],
            options={
                'verbose_name': 'Municipio',
                'verbose_name_plural': 'Municipios',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Servidor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('foto', models.ImageField(blank=True, null=True, upload_to='fotos', verbose_name='Foto')),
                ('matricula', sloth.db.models.CharField(max_length=255, verbose_name='Matrícula')),
                ('nome', sloth.db.models.CharField(max_length=255, verbose_name='Nome')),
                ('cpf', sloth.db.models.CharField(max_length=255, verbose_name='CPF')),
                ('data_nascimento', models.DateField(null=True, verbose_name='Data de Nascimento')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('endereco', sloth.db.models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='base.endereco', verbose_name='Endereço')),
                ('naturalidade', sloth.db.models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='base.municipio', verbose_name='Naturalidade')),
            ],
            options={
                'verbose_name': 'Servidor',
                'verbose_name_plural': 'Servidores',
                'icon': 'file-earmark-person',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Telefone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ddd', models.PositiveIntegerField(verbose_name='DDD')),
                ('numero', sloth.db.models.CharField(max_length=255, verbose_name='Número')),
            ],
            options={
                'verbose_name': 'Telefone',
                'verbose_name_plural': 'Telefones',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='UnidadeOrganizacional',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sigla', sloth.db.models.CharField(max_length=255, verbose_name='Sigla')),
                ('diretor', sloth.db.models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='base.servidor', verbose_name='Diretor')),
                ('instituto', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.instituto', verbose_name='Instituto')),
            ],
            options={
                'verbose_name': 'Campus',
                'verbose_name_plural': 'Campi',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Setor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sigla', sloth.db.models.CharField(max_length=255, verbose_name='Sigla')),
                ('chefe', sloth.db.models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='chefia', to='base.servidor', verbose_name='Chefe')),
                ('substitutos_eventuais', models.ManyToManyField(blank=True, related_name='substituicao_chefia', to='base.Servidor', verbose_name='Substituto Eventuais')),
                ('uo', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.unidadeorganizacional', verbose_name='Campus')),
            ],
            options={
                'verbose_name': 'Setor',
                'verbose_name_plural': 'Setor',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.AddField(
            model_name='servidor',
            name='setor',
            field=sloth.db.models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='base.setor', verbose_name='Setor'),
        ),
        migrations.AddField(
            model_name='servidor',
            name='user',
            field=sloth.db.models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Usuário'),
        ),
        migrations.AddField(
            model_name='instituto',
            name='reitor',
            field=sloth.db.models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='base.servidor', verbose_name='Reitor'),
        ),
        migrations.CreateModel(
            name='Frequencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('horario', models.DateTimeField(verbose_name='Horário')),
                ('homologado', models.BooleanField(default=False, verbose_name='Homologado')),
                ('servidor', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.servidor', verbose_name='Servidor')),
            ],
            options={
                'verbose_name': 'Frequência',
                'verbose_name_plural': 'Frequências',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.CreateModel(
            name='Ferias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ano', models.IntegerField(verbose_name='Ano')),
                ('inicio', models.DateField(verbose_name='Início')),
                ('fim', models.DateField(verbose_name='Fim')),
                ('servidor', sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.servidor', verbose_name='Servidor')),
            ],
            options={
                'verbose_name': 'Férias',
                'verbose_name_plural': 'Férias',
            },
            bases=(models.Model, sloth.core.base.ModelMixin),
        ),
        migrations.AddField(
            model_name='estado',
            name='cidades_metropolitanas',
            field=models.ManyToManyField(blank=True, related_name='s1', to='base.Municipio', verbose_name='Cidades Metropolitanas'),
        ),
        migrations.AddField(
            model_name='estado',
            name='endereco',
            field=sloth.db.models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='base.endereco', verbose_name='Endereço'),
        ),
        migrations.AddField(
            model_name='estado',
            name='telefones',
            field=sloth.db.models.OneToManyField(to='base.Telefone', verbose_name='Telefones'),
        ),
        migrations.AddField(
            model_name='endereco',
            name='municipio',
            field=sloth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.municipio', verbose_name='Município'),
        ),
    ]