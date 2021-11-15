# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from sloth.db import models, meta, role


@role('Administrador', 'user')
class Administrador(models.Model):
    nome = models.CharField('Nome')
    cpf = models.CharField('CPF', rmask='000.000.000-00')

    user = models.ForeignKey(User, verbose_name='Usuário', blank=True)

    class Meta:
        verbose_name = 'Administrador'
        verbose_name_plural = 'Administradores'
        fieldsets = {
            'Dados Gerais': ('nome', 'cpf')
        }

    def save(self, *args, **kwargs):
        self.user = User.objects.get_or_create(
            username=self.cpf, defaults={}
        )[0]
        self.user.set_password('123')
        self.user.save()
        super().save()


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
        verbose_name = 'Categoria de Investimento'
        verbose_name_plural = 'Categorias de Investimento'
        list_display = 'nome', 'get_subcategorias'
        can_admin = 'Administrador',

    def __str__(self):
        return self.nome

    def view(self):
        return self.values('get_dados_gerais', 'get_subcategorias', 'get_perguntas')

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
        ).actions('delete').template('adm/queryset/accordion')


class Subcategoria(models.Model):
    categoria = models.ForeignKey(Categoria, verbose_name='Categoria')
    nome = models.CharField(verbose_name='Nome')

    class Meta:
        verbose_name = 'Subcategoria'
        verbose_name_plural = 'Subcategorias'
        can_delete = 'Administrador',
        can_edit = 'Administrador',

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
    BOOLEANO = 6
    OPCOES = 7

    TIPOS_RESPOSTA_CHOICES = [
        [1, 'Texto Curto'],
        [2, 'Texto Longo'],
        [3, 'Número Decimal'],
        [4, 'Número Inteiro'],
        [5, 'Data'],
        [6, 'Sim/Não'],
        [7, 'Múltiplas Escolhas'],
    ]
    categoria = models.ForeignKey(Categoria, verbose_name='Categoria')
    texto = models.CharField(verbose_name='Texto')
    obrigatoria = models.BooleanField(verbose_name='Obrigatória', blank=True)
    tipo_resposta = models.IntegerField(verbose_name='Tipo de Resposta', choices=TIPOS_RESPOSTA_CHOICES)
    opcoes = models.OneToManyField(OpcaoResposta, verbose_name='Opções de Resposta', blank=True)

    class Meta:
        verbose_name = 'Pergunta'
        verbose_name_plural = 'Perguntas'
        list_display = 'categoria', 'texto', 'obrigatoria', 'get_tipo_resposta'
        can_delete = 'Administrador',
        can_edit = 'Administrador',

    def __str__(self):
        return '{}'.format(self.texto)

    @meta('Tipo de Resposta')
    def get_tipo_resposta(self):
        return self.get_tipo_resposta_display()


class Instituicao(models.Model):
    nome = models.CharField(verbose_name='Nome')
    sigla = models.CharField(verbose_name='Sigla')

    class Meta:
        verbose_name = 'Instituição'
        verbose_name_plural = 'Instituições'
        can_admin = 'Administrador',
        icon = 'building'

    def __str__(self):
        return self.sigla

    def view(self):
        return self.values('get_dados_gerais', 'get_gestores', 'get_campi')

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('nome', 'sigla')

    @meta('Campi')
    def get_campi(self):
        return self.campus_set.ignore('instituicao').global_actions('AdicionarCampus').actions('edit', 'delete')

    @meta('Gestores')
    def get_gestores(self):
        return self.gestor_set.ignore('instituicao').global_actions('AdicionarGestor').actions('edit', 'delete')


class Campus(models.Model):
    instituicao = models.ForeignKey(Instituicao, verbose_name='Campus')
    nome = models.CharField(verbose_name='Nome')
    sigla = models.CharField(verbose_name='Sigla')

    class Meta:
        verbose_name = 'Campus'
        verbose_name_plural = 'Campi'

    def __str__(self):
        return '{}/{}'.format(self.sigla, self.instituicao)


@role('Gestor', 'user', instituicao='instituicao')
class Gestor(models.Model):
    nome = models.CharField('Nome')
    cpf = models.CharField('CPF', rmask='000.000.000-00')
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituição')

    user = models.ForeignKey(User, verbose_name='Usuário', blank=True)

    class Meta:
        verbose_name = 'Gestor '
        verbose_name_plural = 'Gestores'
        fieldsets = {
            'Dados Gerais': (('nome', 'cpf'), 'instituicao')
        }
        can_admin = 'Administrador',

    def save(self, *args, **kwargs):
        self.user = User.objects.get_or_create(
            username=self.cpf, defaults={}
        )[0]
        self.user.set_password('123')
        self.user.save()
        super().save()


class CicloManager(models.Manager):
    @meta('Ciclos', roles=('Administrador',))
    def all(self):
        return super().all().template('adm/queryset/accordion')

    @meta('Ciclos Abertos', roles=('Administrador',))
    def abertos(self):
        return super().all()


class Ciclo(models.Model):
    ano = models.ForeignKey(Ano, verbose_name='Ano')
    inicio = models.DateField(verbose_name='Início')
    fim = models.DateField(verbose_name='Fim')
    teto = models.DecimalField(verbose_name='Teto (R$)')
    prioridades = models.IntegerField(verbose_name='Quantidade', choices=[[x, x] for x in range(1, 11)])
    instituicoes = models.ManyToManyField(Instituicao, verbose_name='Demandantes', blank=True)

    objects = CicloManager()

    class Meta:
        icon = 'arrow-clockwise'
        verbose_name = 'Ciclo de Demanda'
        verbose_name_plural = 'Ciclos de Demandas'
        can_admin = 'Administrador',
        fieldsets = {
            'Dados Gerais': ('ano', ('inicio', 'fim'),),
            'Limite Finaneiro': ('teto',),
            'Demandas': ('prioridades', 'instituicoes'),
        }

    def __str__(self):
        return 'Ciclo de investimentos para {}'.format(self.ano)

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('ano', ('inicio', 'fim'), ('teto', 'prioridades'))

    @meta('Demandas')
    def get_demandas(self):
        return self.demanda_set.all().ignore('ciclo')

    def view(self):
        return self.values('get_dados_gerais', 'get_demandas')

    def gerar_demandas(self):
        if not self.demanda_set.exists():
            for prioridade in range(1, self.prioridades + 1):
                for instituicao in self.instituicoes.all():
                    lookups = dict(ciclo=self, prioridade=prioridade, instituicao=instituicao)
                    if not Demanda.objects.filter(**lookups).exists():
                        Demanda.objects.create(**lookups)

    def gerar_questionarios(self):
        for demanda in self.demanda_set.filter(classificacao__isnull=False):
            questionario = Questionario.objects.filter(demanda=demanda).first()
            if questionario is None:
                questionario = Questionario.objects.create(demanda=demanda)
            for pergunta in demanda.classificacao.categoria.pergunta_set.all():
                lookups = dict(questionario=questionario, pergunta=pergunta)
                if not PerguntaQuestionario.objects.filter(**lookups).exists():
                    PerguntaQuestionario.objects.create(**lookups)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for instituicao in self.instituicoes.all():
            for i in range(1, self.prioridades+1):
                prioridade = Prioridade.objects.get_or_create(numero=i)[0]
                lookups = dict(ciclo=self, instituicao=instituicao, prioridade=prioridade)
                if not Demanda.objects.filter(**lookups).exists():
                    Demanda.objects.create(**lookups)
        self.gerar_demandas()
        self.gerar_questionarios()


class DemandaManager(models.Manager):
    @meta('Todas', roles=('Gestor',))
    def all(self):
        return self.list_display(
            'ciclo', 'instituicao', 'get_prioridade', 'get_detalhamento', 'get_progresso_questionario'
        ).attach(
            'aguardando_detalhamento', 'aguardando_esclarecimentos', 'get_total_por_instituicao'
        ).role_lookups('Gestor', instituicao='instituicao')

    @meta('Aguardando Detalhamento')
    def aguardando_detalhamento(self):
        return self.list_display('ciclo', 'instituicao', 'get_prioridade').filter(classificacao__isnull=True).actions(
            'DetalharDemanda'
        ).role_lookups('Gestor', instituicao='instituicao')

    @meta('Aguardando Justificativas')
    def aguardando_esclarecimentos(self):
        return self.all().filter(classificacao__isnull=False).actions(
            'ResponderQuestionario'
        ).role_lookups('Gestor', instituicao='instituicao')

    @meta('Total por Instituição')
    def get_total_por_instituicao(self):
        return self.filter(valor__isnull=False).sum('valor', 'instituicao')


class Demanda(models.Model):
    ciclo = models.ForeignKey(Ciclo, verbose_name='Ciclo')
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituição')
    descricao = models.TextField(verbose_name='Descrição')
    prioridade = models.ForeignKey(Prioridade, verbose_name='Prioridade')
    classificacao = models.ForeignKey(Subcategoria, verbose_name='Classificação', null=True)
    valor = models.DecimalField(verbose_name='Valor (R$)', null=True)

    objects = DemandaManager()

    class Meta:
        verbose_name = 'Demanda'
        verbose_name_plural = 'Demandas'
        can_view = 'Administrador', 'Gestor'

    def __str__(self):
        return 'Demanda '.format(self.pk)

    def get_questionario(self):
        return self.questionario_set.first()

    @meta('Detalhamento')
    def get_detalhamento(self):
        return self.values('descricao', 'classificacao', 'valor')

    @meta('Perguntas Obrigatórias')
    def get_total_perguntas(self):
        return self.get_questionario().perguntaquestionario_set.filter(pergunta__obrigatoria=True).count() if self.get_questionario() else 0

    @meta('Total de Respostas')
    def get_total_respostas(self):
        return self.get_questionario().perguntaquestionario_set.filter(pergunta__obrigatoria=True, resposta__isnull=False).count() if self.get_questionario() else 0

    @meta('Questionário')
    def get_dados_questionario(self):
        return self.values('get_total_perguntas', 'get_total_respostas', 'get_progresso_questionario')

    @meta('Respostas do Questionário', template='adm/formatters/progress')
    def get_progresso_questionario(self):
        total_perguntas = self.get_total_perguntas()
        total_respostas = self.get_total_respostas()
        if total_perguntas:
            return int(total_respostas * 100 / total_perguntas)
        return 0

    @meta('Prioridade', template='prioridade')
    def get_prioridade(self):
        return self.prioridade

    def get_cor(self):
        return ['cb4335', 'ec7063', 'f1948a', 'f5b7b1', 'fadbd8'][self.prioridade.numero-1]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.classificacao:
            self.ciclo.gerar_questionarios()


class Questionario(models.Model):
    demanda = models.ForeignKey(Demanda, verbose_name='Demanda')

    class Meta:
        verbose_name = 'Questionário'
        verbose_name_plural = 'Questionários'

    def __str__(self):
        return '{} - {}'.format(self.demanda.instituicao, self.demanda.ciclo)


class PerguntaQuestionario(models.Model):
    questionario = models.ForeignKey(Questionario, verbose_name='Questionário')
    pergunta = models.ForeignKey(Pergunta, verbose_name='Pergunta')
    resposta = models.TextField(verbose_name='Resposta', null=True)

    class Meta:
        verbose_name = 'Resposta de Questionário'
        verbose_name_plural = 'Respostas de Questionário'
        can_list = 'Administrador',
        list_display = 'get_ciclo', 'get_instituicao', 'get_demanda', 'pergunta', 'resposta'
        list_filter = 'questionario__demanda__instituicao', 'questionario__demanda__ciclo'

    @meta('Demanda')
    def get_demanda(self):
        return self.questionario.demanda.descricao

    @meta('Ciclo')
    def get_ciclo(self):
        return self.questionario.demanda.ciclo.ano

    @meta('Instituição')
    def get_instituicao(self):
        return self.questionario.demanda.instituicao

    def __str__(self):
        return '{} - {}'.format(self.pergunta, self.resposta)
