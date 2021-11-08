# -*- coding: utf-8 -*-
from django.contrib.auth.models import User

from dms2.db import models

from dms2.db.models.decorators import meta, role


class Telefone(models.Model):
    ddd = models.PositiveIntegerField(verbose_name='DDD')
    numero = models.CharField(verbose_name='Número', mask='00000-0000')

    def __str__(self):
        return '({}) - {}'.format(self.ddd, self.numero)

    class Meta:
        verbose_name = 'Telefone'
        verbose_name_plural = 'Telefones'


class EstadoManager(models.Manager):

    @meta('Todos')
    def all(self):
        return super().all().list_display(
            'sigla', 'cidades_metropolitanas', 'endereco', 'telefones'
        ).actions(
            'EditarSiglaEstado',
        ).global_actions('FazerAlgumaCoisa').batch_actions('EditarSiglaEstado')


class Estado(models.Model):
    sigla = models.CharField('Sigla')
    cidades_metropolitanas = models.ManyToManyField('base.Municipio', verbose_name='Cidades Metropolitanas', blank=True, related_name='s1')
    endereco = models.OneToOneField('base.Endereco', verbose_name='Endereço', null=True, blank=True)
    telefones = models.OneToManyField(Telefone, verbose_name='Telefones')

    objects = EstadoManager()

    class Meta:
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'
        add_form = 'EstadoForm'

    def __str__(self):
        return self.sigla

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('id', ('sigla', 'endereco'))

    def view(self):
        return self.values('get_dados_gerais', 'get_cidades').actions(
            'FazerAlgumaCoisa', 'Edit', 'InformarCidadesMetropolitanas'
        )

    def _can_view_sigla(self, user):
        return not user.is_superuser

    @meta('Cidades')
    def get_cidades(self):
        return self.municipio_set.get_queryset().actions('Edit').relation_actions(
            'AdicionarMunicipioEstado'
        )


class MunicipioManager(models.Manager):

    @meta('Todos')
    def all(self):
        return self.attach('potiguares', 'get_qtd_por_estado')

    @meta('Potiguares')
    def potiguares(self):
        return self.filter(estado__sigla='RN')

    @meta('Quantidade por Estado')
    def get_qtd_por_estado(self):
        return self.count('estado')


class Municipio(models.Model):
    nome = models.CharField('Nome')
    estado = models.ForeignKey(Estado, verbose_name='Estado')

    objects = MunicipioManager()

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

    @meta('Dados Gerais2')
    def get_dados_gerais2(self):
        return self.values(('get_a', 'get_b', 'get_c', 'get_d'))

    def view(self):
        # return super().view()
        # return self.values('get_dados_gerais', 'get_dados_gerais2')
        # return self.values(('nome', 'estado'), 'get_progresso')
        return self.values('get_dados_gerais', 'get_dados')

    @meta('Dados')
    def get_dados(self):
        return self.values('get_dados_gerais', 'get_dados_gerais2')

    def has_edit_permission(self, user):
        return self.pk % 2 == 0

    @meta('Nome')
    def get_a(self):
        return 'Carlos Breno Pereira Silva'

    @meta('Data de Nascimento')
    def get_b(self):
        return '27/08/1984'

    @meta('CPF')
    def get_c(self):
        return '047.704.024-14'

    @meta('R$')
    def get_d(self):
        return 'R$ 23.00,99'


class Endereco(models.Model):
    logradouro = models.CharField('Logradouro')
    numero = models.CharField('Número')
    municipio = models.ForeignKey(Municipio, verbose_name='Município')

    class Meta:
        verbose_name = 'Endereço'
        verbose_name_plural = 'Endereços'
        fieldsets = {
            'Dados Gerais': ('logradouro', ('numero', 'municipio'))
        }

    def __str__(self):
        return '{}, {}, {}'.format(self.logradouro, self.numero, self.municipio)


class Instituto(models.Model):
    sigla = models.CharField(verbose_name='Sigla')
    reitor = models.ForeignKey('base.Servidor', verbose_name='Reitor', null=True, blank=True)

    class Meta:
        verbose_name = 'Instituto'
        verbose_name_plural = 'Instituto'
        list_template = 'adm/queryset/cards'

    def __str__(self):
        return self.sigla


class UnidadeOrganizacional(models.Model):
    instituto = models.ForeignKey(Instituto, verbose_name='Instituto')
    sigla = models.CharField(verbose_name='Sigla')
    diretor = models.ForeignKey('base.Servidor', verbose_name='Diretor', null=True, blank=True)

    class Meta:
        verbose_name = 'Campus'
        verbose_name_plural = 'Campi'

    def __str__(self):
        return '{}/{}'.format(self.sigla, self.instituto)


@role('Chefe', 'chefe__user', setor='id')
@role('Substituto Eventual', 'substitutos_eventuais__user', setor='id')
class Setor(models.Model):
    uo = models.ForeignKey(UnidadeOrganizacional, verbose_name='Campus')
    sigla = models.CharField(verbose_name='Sigla')
    chefe = models.ForeignKey('base.Servidor', verbose_name='Chefe', null=True, related_name='chefia', blank=True)
    substitutos_eventuais = models.ManyToManyField(
        'base.Servidor', verbose_name='Substituto Eventuais', related_name='substituicao_chefia', blank=True
    )

    class Meta:
        verbose_name = 'Setor'
        verbose_name_plural = 'Setor'

    def __str__(self):
        return '{}/{}'.format(self.sigla, self.uo)


class ServidorManager(models.Manager):

    @meta('Todos')
    def all(self):
        return self.list_display(
            'get_dados_gerais', 'ativo', 'naturalidade'
        ).list_filter(
            'data_nascimento', 'ativo', 'naturalidade'
        ).search_fields('nome').ordering(
            'nome', 'ativo', 'data_nascimento'
        ).attach(
            'com_endereco', 'sem_endereco', 'ativos', 'inativos'
        ).actions(
            'CorrigirNomeServidor', 'FazerAlgumaCoisa', 'DefinirSetor'
        ).global_actions(
            'FazerAlgumaCoisa'
        )   # .template('servidores')

    @meta('Com Endereço')
    def com_endereco(self):
        return self.filter(endereco__isnull=False).actions('CorrigirNomeServidor')

    @meta('Sem Endereço')
    def sem_endereco(self):
        return self.filter(endereco__isnull=True)

    @meta('Ativos')
    def ativos(self):
        return self.filter(ativo=True).batch_actions('InativarServidores')

    @meta('Inativos')
    def inativos(self):
        return self.filter(ativo=False).actions('AtivarServidor')


@role('Servidor', 'user', servidor='id', setor='setor', uo='setor__uo', instituto='setor__uo__instituto')
class Servidor(models.Model):
    foto = models.ImageField(verbose_name='Foto', null=True, blank=True, upload_to='fotos')
    matricula = models.CharField('Matrícula')
    nome = models.CharField('Nome')
    cpf = models.CharField('CPF', rmask='000.000.000-00')
    data_nascimento = models.DateField('Data de Nascimento', null=True)
    endereco = models.OneToOneField(Endereco, verbose_name='Endereço', null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    naturalidade = models.ForeignKey(Municipio, verbose_name='Naturalidade', null=True)
    setor = models.ForeignKey(Setor, verbose_name='Setor', null=True, blank=True)

    user = models.ForeignKey(User, verbose_name='Usuário', null=True, blank=True)

    objects = ServidorManager()

    class Meta:
        icon = 'file-earmark-person'
        verbose_name = 'Servidor'
        verbose_name_plural = 'Servidores'
        form = 'ServidorForm'
        list_template = 'adm/queryset/rows'

    def __str__(self):
        return self.nome

    def has_get_dados_gerais_permission(self, user):
        return self and user.is_superuser

    @meta('Foto')
    def get_foto(self):
        return self.foto # or '/static/images/profile.png'

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
        ).actions('InformarEndereco', 'ExcluirEndereco') if self.endereco_id else self.values('endereco')

    def view(self):
        return self.values(
            'get_dados_gerais', 'get_total_ferias_por_ano', 'get_dados_recursos_humanos', 'get_ferias'
        ).actions('InformarEndereco', 'CorrigirNomeServidor1', 'Edit').attach('get_ferias').append(
            'get_endereco', 'get_total_ferias_por_ano', 'get_frequencias'
        )

    @meta('Frequências')
    def get_frequencias(self):
        return self.frequencia_set.limit_per_page(3).relation_actions('RegistrarPonto').actions(
            'HomologarFrequencia').batch_actions('FazerAlgumaCoisa').ignore('servidor').template('adm/queryset/accordion')

    @meta('Férias')
    def get_ferias(self):
        return self.ferias_set.list_display(
            'ano', 'inicio', 'fim'
        ).actions('AlterarFerias', 'ExcluirFerias').global_actions('CadastrarFerias').template('adm/queryset/timeline')

    @meta('Recursos Humanos')
    def get_dados_recursos_humanos(self):
        return self.values('get_ferias', 'get_endereco', 'get_frequencias').actions('FazerAlgumaCoisa')

    @meta('Férias por Ano')
    def get_total_ferias_por_ano(self):
        return self.get_ferias().count('ano')

    def save(self, *args, **kwargs):
        self.user = User.objects.get_or_create(
            username=self.cpf, defaults={}
        )[0]
        super().save()


class FeriasManager(models.Manager):

    @meta('Ferias')
    def all(self):
        return self.list_display(
            'servidor', 'ano', 'get_periodo2'
        ).search_fields(
            'servidor__matricula', 'servidor__nome'
        ).list_filter('servidor', 'ano').ordering(
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

    objects = FeriasManager()

    class Meta:
        verbose_name = 'Férias'
        verbose_name_plural = 'Férias'

    @meta('Período')
    def get_periodo(self):
        return 'de {} a {}'.format(self.inicio, self.fim)

    @meta('Período')
    def get_periodo2(self):
        return self.values('inicio', 'fim')

    def __str__(self):
        return 'Férias do ano {}'.format(self.ano)


class Frequencia(models.Model):
    servidor = models.ForeignKey(Servidor, verbose_name='Servidor')
    horario = models.DateTimeField('Horário')
    homologado = models.BooleanField('Homologado', default=False)

    class Meta:
        verbose_name = 'Frequência'
        verbose_name_plural = 'Frequências'
        list_template = 'adm/queryset/timeline'

    def __str__(self):
        return 'Resistro {}'.format(self.id)
