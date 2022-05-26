# -*- coding: utf-8 -*-

from sloth.db import models, role, meta


@role('Gerente', username='email')
class Gerente(models.Model):
    nome = models.CharField(verbose_name='None')
    email = models.EmailField(verbose_name='Email')

    class Meta:
        verbose_name = 'Gerente'
        verbose_name_plural = 'Gerentes'

    def __str__(self):
        return self.nome


class Telefone(models.Model):
    ddd = models.PositiveIntegerField(verbose_name='DDD')
    numero = models.CharField(verbose_name='Número', mask='00000-0000')

    def __str__(self):
        return '({}) - {}'.format(self.ddd, self.numero)

    class Meta:
        verbose_name = 'Telefone'
        verbose_name_plural = 'Telefones'


class EstadoManager(models.Manager):

    def all(self):
        return super().all().display(
            'sigla', 'cidades_metropolitanas', 'endereco', 'telefones'
        ).actions(
            'EditarSiglaEstado',
        ).global_actions('FazerAlgumaCoisa').batch_actions('EditarSiglaEstado')


class Estado(models.Model):
    sigla = models.CharField('Sigla')
    cidades_metropolitanas = models.ManyToManyField('base.Municipio', verbose_name='Cidades Metropolitanas', blank=True, related_name='s1')
    endereco = models.OneToOneField('base.Endereco', verbose_name='Endereço', null=True, blank=False)
    telefones = models.OneToManyField(Telefone, verbose_name='Telefones', min=2, max=2)
    historia = models.TextField(verbose_name='História', formatted=True)

    objects = EstadoManager()

    class Meta:
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'

    def __str__(self):
        return self.sigla

    @meta('História', 'utils/formatted')
    def get_historia(self):
        return self.historia

    def get_dados_gerais(self):
        return self.values('id', ('sigla', 'endereco'), 'get_historia')

    def view(self):
        return self.values('get_dados_gerais', 'get_cidades').actions(
            'FazerAlgumaCoisa', 'Edit', 'InformarCidadesMetropolitanas'
        )

    def get_cidades(self):
        return self.municipio_set.get_queryset().actions('Edit').global_actions(
            'AdicionarMunicipioEstado'
        )

    def has_list_permission(self, user):
        return user.roles.contains('Chefe')


class MunicipioManager(models.Manager):

    def all(self):
        return self.attach('agrupados', 'get_qtd_por_estado')

    def potiguares(self):
        return self.filter(estado__sigla='RN')

    def paraibanos(self):
        return self.filter(estado__sigla='PB')

    def agrupados(self):
        return self.valueset('potiguares', 'paraibanos', 'get_qtd_por_estado')

    def get_qtd_por_estado(self):
        return self.count('estado').verbose_name('Quantidade por Estado')


class Municipio(models.Model):
    nome = models.CharField('Nome')
    estado = models.ForeignKey(Estado, verbose_name='Estado')

    objects = MunicipioManager()

    class Meta:
        verbose_name = 'Municipio'
        verbose_name_plural = 'Municipios'

    def __str__(self):
        return '{}/{}'.format(self.nome, self.estado)

    @meta('Progresso', 'app/formatters/progress')
    def get_progresso(self):
        return 27

    def get_dados_gerais(self):
        return self.values('id', ('nome', 'estado'), 'get_progresso')

    def get_dados_gerais2(self):
        return self.values(('get_a', 'get_b', 'get_c', 'get_d'))

    def view(self):
        # return super().view()
        # return self.values('get_dados_gerais', 'get_dados_gerais2')
        # return self.values(('nome', 'estado'), 'get_progresso')
        return self.values('get_dados_gerais', 'get_dados')

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


class InstitutoManager(models.Manager):
    def all(self):
        return self.cards()


class Instituto(models.Model):
    sigla = models.CharField(verbose_name='Sigla')
    reitor = models.ForeignKey('base.Servidor', verbose_name='Reitor', null=True, blank=True)

    objects = InstitutoManager()

    class Meta:
        verbose_name = 'Instituto'
        verbose_name_plural = 'Instituto'

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


@role('Chefe', 'chefe__matricula')
@role('Substituto Eventual', 'substitutos_eventuais__matricula', setor='id')
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

    def view(self):
        return self.values(('uo', 'sigla'), 'chefe', 'substitutos_eventuais')



class ServidorManager(models.Manager):

    def all(self):
        return self.display(
            'foto', 'get_dados_gerais', 'ativo', 'naturalidade', 'setor'
        ).filters(
            'data_nascimento', 'ativo', 'naturalidade'
        ).search('nome').ordering(
            'nome', 'ativo', 'data_nascimento'
        ).attach(
            'com_endereco', 'sem_endereco', 'ativos', 'inativos', 'total_por_situacao', 'get_estatisticas'
        ).actions(
            'CorrigirNomeServidor', 'FazerAlgumaCoisa', 'DefinirSetor'
        ).batch_actions(
            'DefinirSetor'
        ).global_actions(
            'FazerAlgumaCoisa'
        ).cards()

    def com_endereco(self):
        return self.display('get_foto', 'get_dados_gerais').filter(endereco__isnull=False).actions('CorrigirNomeServidor')

    def sem_endereco(self):
        return self.display('get_dados_gerais', 'ativo', 'naturalidade', 'setor').filter(endereco__isnull=True).cards()#.view('get_total_ferias_por_ano')

    def ativos(self):
        return self.display('get_dados_gerais', 'ativo', 'naturalidade', 'setor').filter(ativo=True).batch_actions('InativarServidores').rows()

    def inativos(self):
        return self.filter(ativo=False).actions('AtivarServidor')

    def total_por_situacao(self):
        return self.count('ativo').bar_chart()

    def total_por_setor_e_ativo(self):
        return self.count('setor', 'ativo').pie_chart()

    def get_estatisticas(self):
        return self.valueset('total_por_setor_e_ativo', 'total_por_situacao')


@role('Servidor', 'matricula', setor='setor', uo='setor__uo', instituto='setor__uo__instituto')
class Servidor(models.Model):
    foto = models.ImageField(verbose_name='Foto', null=True, blank=True, upload_to='fotos')
    matricula = models.CharField('Matrícula')
    nome = models.CharField('Nome')
    cpf = models.BrCpfField('CPF')
    data_nascimento = models.DateField('Data de Nascimento', null=True)
    endereco = models.OneToOneField(Endereco, verbose_name='Endereço', null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    naturalidade = models.ForeignKey(Municipio, verbose_name='Naturalidade', null=True)
    setor = models.ForeignKey(Setor, verbose_name='Setor', null=True, blank=True)

    objects = ServidorManager()

    class Meta:
        icon = 'file-earmark-person'
        verbose_name = 'Servidor'
        verbose_name_plural = 'Servidores'
        select_fields = 'get_foto', 'nome', 'matricula', 'cpf'

    def __str__(self):
        return self.nome

    def has_get_dados_gerais_permission(self, user):
        return self and user.is_superuser

    @meta('Foto', 'app/formatters/image')
    def get_foto(self):
        return self.foto or '/static/images/profile.png'

    @meta('Progresso', 'app/formatters/progress')
    def get_progresso(self):
        return 27

    def get_dados_gerais(self):
        return self.values(
            'nome', ('cpf', 'data_nascimento'), 'get_progresso'
        ).actions('CorrigirNomeServidor1', 'FazerAlgumaCoisa').image('get_foto')

    def get_endereco(self):
        return self.endereco.values(
            'logradouro', ('logradouro', 'numero'), ('municipio', 'municipio__estado')
        ).actions('InformarEndereco', 'ExcluirEndereco') if self.endereco_id else self.values(
            'endereco'
        ).actions('InformarEndereco')

    def view(self):
        return self.values(
            'get_dados_gerais', 'get_total_ferias_por_ano', 'get_dados_recursos_humanos', 'get_dados_ferias2'
        ).actions(
            'InformarEndereco', 'CorrigirNomeServidor1', 'Edit'
        ).append(
            'get_endereco', 'get_total_ferias_por_ano2', 'get_frequencias'
        ).attach(
            'get_ferias', 'get_frequencias'
        )

    def get_frequencias(self):
        return self.frequencia_set.limit_per_page(3).global_actions('RegistrarPonto').actions(
            'HomologarFrequencia').batch_actions('FazerAlgumaCoisa').ignore('servidor').accordion()

    def get_ferias(self):
        return self.ferias_set.display(
            'ano', 'inicio', 'fim'
        ).actions(
            'AlterarFerias', 'ExcluirFerias'
        ).global_actions(
            'CadastrarFerias'
        ).timeline().ignore('servidor')

    def get_dados_recursos_humanos(self):
        return self.values('get_endereco', 'get_dados_ferias', 'get_frequencias').actions('FazerAlgumaCoisa')

    def get_total_ferias_por_ano(self):
        return self.get_ferias().count('ano').chart('column')

    def get_total_ferias_por_ano2(self):
        return self.get_ferias().count('ano').chart('bar')

    def get_dados_ferias(self):
        return self.values('get_ferias', 'get_total_ferias_por_ano')

    def get_dados_ferias2(self):
        return self.get_dados_ferias()


class FeriasManager(models.Manager):

    def all(self):
        return self.display(
            'servidor', 'ano', 'get_periodo2'
        ).search(
            'servidor__matricula', 'servidor__nome'
        ).filters('servidor', 'ano').ordering(
            'inicio', 'fim'
        ).actions('EditarFerias').attach('total_por_ano_servidor')

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

    def get_periodo(self):
        return 'de {} a {}'.format(self.inicio, self.fim)

    def get_periodo2(self):
        return self.values('inicio', 'fim')

    def __str__(self):
        return 'Férias do ano {}'.format(self.ano)


class FrequenciaManager(models.Manager):
    def all(self):
        return self.timeline()


class Frequencia(models.Model):
    servidor = models.ForeignKey(Servidor, verbose_name='Servidor')
    horario = models.DateTimeField('Horário')
    homologado = models.BooleanField('Homologado', default=False)

    objects = FrequenciaManager()

    class Meta:
        verbose_name = 'Frequência'
        verbose_name_plural = 'Frequências'

    def __str__(self):
        return 'Resistro {}'.format(self.id)
