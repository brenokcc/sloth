# -*- coding: utf-8 -*-

from django.db import models

from dms2.db.models.decorators import meta


class EstadoSet(models.QuerySet):

    @meta('Todos')
    def all(self):
        return super().all().display(
            'sigla', 'cidades_metropolitanas'
        ).actions('FazerAlgumaCoisa', 'EditarSiglaEstado', 'EditarSiglasEstado')


class Estado(models.Model):
    sigla = models.CharField('Sigla')
    cidades_metropolitanas = models.ManyToManyField('base.Municipio', verbose_name='Cidades Metropolitanas', blank=True, related_name='s1')

    class Meta:
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'

    def __str__(self):
        return self.sigla

    def view(self):
        return super().view().actions('FazerAlgumaCoisa', 'Edit')


class MunicipioSet(models.QuerySet):

    def all(self):
        return self.attach('ativos', 'get_qtd_por_estado')

    @meta('Ativos')
    def ativos(self):
        return self.filter(pk=1)

    @meta('Quantidade por Estado')
    def get_qtd_por_estado(self):
        return self.count('estado')


class Municipio(models.Model):
    nome = models.CharField('Nome')
    estado = models.ForeignKey(Estado, verbose_name='Estado')

    class Meta:
        verbose_name = 'Municipio'
        verbose_name_plural = 'Municipios'

    def __str__(self):
        return '{}/{}'.format(self.nome, self.estado)

    @meta('Progresso', formatter='progress')
    def get_progresso(self):
        return 27

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('id', ('nome', 'estado'), 'get_progresso')

    def view(self):
        return self.values('get_dados_gerais')


class Endereco(models.Model):
    logradouro = models.CharField('Logradouro')
    numero = models.CharField('Número')
    municipio = models.ForeignKey(Municipio, verbose_name='Município')

    class Meta:
        verbose_name = 'Endereço'
        verbose_name_plural = 'Endereços'


class ServidorSet(models.QuerySet):

    @meta('Todos')
    def all(self):
        return super().display(
            'get_dados_gerais', 'ativo', 'naturalidade'
        ).filters(
            'data_nascimento', 'ativo', 'naturalidade'
        ).search('nome').ordering(
            'nome', 'ativo', 'data_nascimento'
        ).attach(
            'com_endereco', 'sem_endereco', 'ativos', 'inativos'
        ).actions('CorrigirNomeServidor', 'FazerAlgumaCoisa')  # .template('servidores')

    @meta('Com Endereço')
    def com_endereco(self):
        return self.filter(endereco__isnull=False).actions('CorrigirNomeServidor')

    @meta('Sem Endereço')
    def sem_endereco(self):
        return self.filter(endereco__isnull=True)

    @meta('Ativos')
    def ativos(self):
        return self.filter(ativo=True).actions('InativarServidores')

    @meta('Inativos')
    def inativos(self):
        return self.filter(ativo=False).actions('AtivarServidor')


class Servidor(models.Model):
    matricula = models.CharField('Matrícula')
    nome = models.CharField('Nome')
    cpf = models.CharField('CPF', rmask='000.000.000-00')
    data_nascimento = models.DateField('Data de Nascimento', null=True)
    endereco = models.OneToOneField(Endereco, verbose_name='Endereço', null=True)
    ativo = models.BooleanField('Ativo', default=True)
    naturalidade = models.ForeignKey(Municipio, verbose_name='Naturalidade', null=True)

    class Meta:
        icon = 'file-earmark-person'
        verbose_name = 'Servidor'
        verbose_name_plural = 'Servidores'

    def __str__(self):
        return self.nome

    def has_get_dados_gerais_permission(self, user):
        return self and user.is_superuser

    def get_foto(self):
        return 'https://www.gravatar.com/avatar/680b8d4a9b843a858148493db5ef0164?s=128&d=identicon&r=PG'

    @meta('Progresso', formatter='progress')
    def get_progresso(self):
        return 27

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('nome', ('cpf', 'data_nascimento'), 'get_progresso').actions('CorrigirNomeServidor1', 'FazerAlgumaCoisa').image('get_foto')  # .template('dados_gerais')

    @meta('Endereço')
    def get_endereco(self):
        return self.endereco.values(
            'logradouro', ('logradouro', 'numero'), ('municipio', 'municipio__estado')
        ).actions('InformarEndereco', 'ExcluirEndereco')

    def view(self):
        return self.values(
            'get_dados_gerais', 'get_total_ferias_por_ano', 'get_dados_recursos_humanos', 'get_ferias'
        ).actions('InformarEndereco', 'CorrigirNomeServidor1').attach('get_ferias').append(
            'get_endereco', 'get_total_ferias_por_ano', 'get_frequencias'
        )

    @meta('Frequências')
    def get_frequencias(self):
        return self.frequencia_set.limit(5)

    @meta('Férias')
    def get_ferias(self):
        return self.ferias_set.display('ano', 'inicio', 'fim').actions('CadastrarFerias', 'AlterarFerias', 'ExcluirFerias')

    @meta('Recursos Humanos')
    def get_dados_recursos_humanos(self):
        return self.values('get_endereco', 'get_ferias', 'get_frequencias').actions('FazerAlgumaCoisa')

    @meta('Férias por Ano')
    def get_total_ferias_por_ano(self):
        return self.get_ferias().count('ano')


class FeriasSet(models.QuerySet):

    @meta('Ferias')
    def all(self):
        return super().all().display(
            'servidor', 'ano', 'get_periodo2'
        ).search(
            'servidor__matricula', 'servidor__nome'
        ).filters('servidor', 'ano').ordering(
            'inicio', 'fim'
        ).actions('EditarFerias').attach('total_por_ano_servidor')

    @meta('Total por Ano e Servidor')
    def total_por_ano_servidor(self):
        return self.count('ano', 'servidor')


class Ferias(models.Model):
    servidor = models.ForeignKey(Servidor, verbose_name='Servidor')
    ano = models.IntegerField('Ano')
    inicio = models.DateField('Início')
    fim = models.DateField('Fim')

    class Meta:
        verbose_name = 'Férias'
        verbose_name_plural = 'Férias'

    @meta('Período')
    def get_periodo(self):
        return 'de {} a {}'.format(self.inicio, self.fim)

    @meta('Período')
    def get_periodo2(self):
        return self.values('inicio', 'fim')


class Frequencia(models.Model):
    servidor = models.ForeignKey(Servidor, verbose_name='Servidor')
    horario = models.DateTimeField('Horário')
    homologado = models.BooleanField('Homologado', default=False)

    class Meta:
        verbose_name = 'Frequência'
        verbose_name_plural = 'Frequências'
