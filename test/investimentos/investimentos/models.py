# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from sloth.db import models, meta


class Ano(models.Model):
    ano = models.IntegerField(verbose_name='Ano')

    class Meta:
        verbose_name = 'Ano'
        verbose_name_plural = 'Anos'

    def __str__(self):
        return '{}'.format(self.ano)


class Prioridade(models.Model):
    numero = models.IntegerField(verbose_name='Número')

    class Meta:
        verbose_name = 'Prioridade'
        verbose_name_plural = 'Prioridades'

    def __str__(self):
        return '{}'.format(self.numero)


class Categoria(models.Model):
    nome = models.CharField(verbose_name='Nome')

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        list_display = 'nome', 'get_subcategorias'

    def __str__(self):
        return self.nome

    def view(self):
        return self.values('get_dados_gerais', 'get_perguntas').append('get_subcategorias')

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('nome')

    @meta('Subcategorias')
    def get_subcategorias(self):
        return self.subcategoria_set.all().ignore('categoria').global_actions(
            'AdicionarSubcategoria'
        ).actions('edit', 'delete')

    @meta('Questionário')
    def get_perguntas(self):
        return self.pergunta_set.all().ignore('categoria').global_actions(
            'AdicionarPergunta'
        ).actions('edit', 'delete').template('adm/queryset/accordion')


class Subcategoria(models.Model):
    categoria = models.ForeignKey(Categoria, verbose_name='Categoria')
    nome = models.CharField(verbose_name='Nome')

    class Meta:
        verbose_name = 'Subcategoria'
        verbose_name_plural = 'Subcategorias'

    def __str__(self):
        return '{} / {}'.format(self.categoria, self.nome)


class OpcaoResposta(models.Model):
    nome = models.CharField(verbose_name='Nome')

    class Meta:
        verbose_name = 'Opção de Resposta'
        verbose_name_plural = 'Opções de Resposta'

    def __str__(self):
        return self.nome


class Pergunta(models.Model):
    TEXTO_CURTO = 1
    TEXTO_LONGO = 2
    NUMERO_DECIMAL = 3
    NUMERO_INTEIRO = 4
    DATA = 5
    OPCOES = 6

    TIPOS_RESPOSTA_CHOICES = [
        [1, 'Texto Curto'],
        [2, 'Texto Longo'],
        [3, 'Número Decimal'],
        [4, 'Número Inteiro'],
        [5, 'Data'],
    ]
    categoria = models.ForeignKey(Categoria, verbose_name='Categoria')
    texto = models.TextField(verbose_name='Texto')
    obrigatoria = models.BooleanField(verbose_name='Obrigatória', blank=True)
    tipo_resposta = models.IntegerField(verbose_name='Tipo de Resposta', choices=TIPOS_RESPOSTA_CHOICES)
    opcoes = models.OneToManyField(OpcaoResposta, verbose_name='Opções de Resposta', blank=True)

    class Meta:
        verbose_name = 'Pergunta'
        verbose_name_plural = 'Perguntas'

    def __str__(self):
        return '{}'.format(self.texto)


class Instituicao(models.Model):
    nome = models.CharField(verbose_name='Nome')
    sigla = models.CharField(verbose_name='Sigla')

    class Meta:
        verbose_name = 'Instituição'
        verbose_name_plural = 'Instituições'

    def __str__(self):
        return self.sigla

    def view(self):
        return self.values('get_dados_gerais', 'get_campi')

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('nome', 'sigla')

    @meta('Campi')
    def get_campi(self):
        return self.campus_set.ignore('instituicao').global_actions('AdicionarCampus').actions('edit', 'delete')


class Campus(models.Model):
    instituicao = models.ForeignKey(Instituicao, verbose_name='Campus')
    nome = models.CharField(verbose_name='Nome')
    sigla = models.CharField(verbose_name='Sigla')

    class Meta:
        verbose_name = 'Campus'
        verbose_name_plural = 'Campi'

    def __str__(self):
        return '{}/{}'.format(self.sigla, self.instituicao)


class Ciclo(models.Model):
    ano = models.ForeignKey(Ano, verbose_name='Ano')
    inicio = models.DateField(verbose_name='Início')
    fim = models.DateField(verbose_name='Fim')
    teto = models.DecimalField(verbose_name='Teto (R$)')
    prioridades = models.IntegerField(verbose_name='Prioridades', choices=[[x, x] for x in range(1, 11)])

    class Meta:
        verbose_name = 'Ciclo de Demanda'
        verbose_name_plural = 'Ciclos de Demandas'

    def __str__(self):
        return 'Ciclo de Demandas {}'.format(self.ano)

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('ano', ('inicio', 'fim'), ('teto', 'prioridades'))

    @meta('Demandas')
    def get_demandas(self):
        return self.demanda_set.all().ignore('ciclo').global_actions(
            'AdicionarInstituicoesCiclo'
        )

    def view(self):
        return self.values('get_dados_gerais', 'get_demandas').append('get_total_por_instituicao')

    @meta('Total por Instituição')
    def get_total_por_instituicao(self):
        return self.demanda_set.filter(valor__isnull=False).sum('valor', 'instituicao')


class DemandaManager(models.Manager):
    @meta('Todas')
    def all(self):
        return self.list_display(
            'ciclo', 'instituicao', 'prioridade', 'classificacao', 'valor'
        ).attach('aguardando_classificacao', 'aguardando_valor', 'aguardando_detalhamento')

    @meta('Aguardando Classificação')
    def aguardando_classificacao(self):
        return self.all().filter(classificacao__isnull=True).actions('ClassificarDemanda')

    @meta('Aguardando Valor')
    def aguardando_valor(self):
        return self.all().filter(valor__isnull=True).actions('InformarValorDemanda')

    @meta('Aguardando Detalhamento')
    def aguardando_detalhamento(self):
        return self.all().filter(prioridade__isnull=False)


class Demanda(models.Model):
    ciclo = models.ForeignKey(Ciclo, verbose_name='Ciclo')
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituição')
    prioridade = models.ForeignKey(Prioridade, verbose_name='Prioridade')
    classificacao = models.ForeignKey(Subcategoria, verbose_name='Classificação', null=True)
    valor = models.DecimalField(verbose_name='Valor (R$)', null=True)

    class Meta:
        verbose_name = 'Demanda'
        verbose_name_plural = 'Demandas'
        fieldsets = {
            'Dados Gerais': ('ciclo', 'instituicao')
        }

    objects = DemandaManager()

    def __str__(self):
        return 'Demanda '.format(self.pk)
