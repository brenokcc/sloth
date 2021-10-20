# -*- coding: utf-8 -*-

from django.db import models

from dms2.db.models.decorators import meta


class Estado(models.Model):
    sigla = models.CharField('Sigla')

    class Meta:
        verbose_name = 'Estado'
        verbose_name_plural = 'Estado'

    def __str__(self):
        return self.sigla


class Municipio(models.Model):
    nome = models.CharField('Nome')
    estado = models.ForeignKey(Estado, verbose_name='Estado')

    class Meta:
        verbose_name = 'Municipio'
        verbose_name_plural = 'Municipios'

    def __str__(self):
        return '{}/{}'.format(self.nome, self.estado)


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
        return super().all().display('get_dados_gerais', 'ativo').allow('AtivarServidor')

    @meta('Com Endereço')
    def com_endereco(self):
        return self.filter(endereco__isnull=False)

    @meta('Sem Endereço')
    def sem_endereco(self):
        return self.filter(endereco__isnull=True)

    @meta('Ativos')
    def ativos(self):
        return self.filter(ativo=True).allow('InativarServidores')

    @meta('Inativos')
    def inativos(self):
        return self.filter(ativo=False)


class Servidor(models.Model):
    matricula = models.CharField('Matrícula')
    nome = models.CharField('Nome')
    cpf = models.CharField('CPF')
    endereco = models.OneToOneField(Endereco, verbose_name='Endereço', null=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Servidor'
        verbose_name_plural = 'Servidores'

    def __str__(self):
        return self.nome

    def has_get_dados_gerais_permission(self, user):
        return self and user.is_superuser

    @meta('Dados Gerais', primary=True)
    def get_dados_gerais(self):
        return self.values('nome', 'cpf').allow('CorrigirNomeServidor', 'FazerAlgumaCoisa')

    @meta('Endereço')
    def get_endereco(self):
        return self.endereco.values(
            'logradouro', ('logradouro', 'numero'), ('municipio', 'municipio__estado')
        ).allow('InformarEndereco', 'ExcluirEndereco')

    def view(self):
        return self.values('get_dados_gerais', 'get_endereco', 'get_dados_recursos_humanos')

    @meta('Frequências')
    def get_frequencias(self):
        return self.frequencia_set.paginate(5)

    @meta('Férias', auxiliary=True)
    def get_ferias(self):
        return self.ferias_set.all().display('ano', 'inicio', 'fim').allow('CadastrarFerias', 'AlterarFerias', 'ExcluirFerias')

    @meta('Recursos Humanos')
    def get_dados_recursos_humanos(self):
        return self.values('get_frequencias', 'get_ferias', 'get_endereco')


class FeriasSet(models.QuerySet):

    @meta('Ferias')
    def all(self):
        return super().all().display('servidor', 'ano', 'get_periodo2').search('servidor__matricula','servidor__nome').filters('servidor','ano').ordering('inicio', 'fim').allow('EditarFerias')


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
