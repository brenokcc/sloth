# -*- coding: utf-8 -*-
import datetime
from datetime import timedelta

from django.contrib.auth.models import User
from sloth.db import models, meta, role


@role('Administrador', 'user')
class Administrador(models.Model):
    nome = models.CharField('Nome')
    cpf = models.CharField('CPF', rmask='000.000.000-00')

    user = models.ForeignKey(User, verbose_name='Usuário', blank=True)

    class Meta:
        icon = 'person-workspace'
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
        icon = 'folder'
        verbose_name = 'Categoria de Investimento'
        verbose_name_plural = 'Categorias de Investimento'
        list_display = 'nome', 'get_quantidade_perguntas'
        can_admin = 'Administrador',

    def __str__(self):
        return self.nome

    def view(self):
        return self.values('get_dados_gerais', 'get_perguntas').append('get_quantidade_perguntas_por_tipo_resposta')

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('nome')

    @meta('Questionário')
    def get_perguntas(self):
        return self.pergunta_set.all().ignore('categoria').global_actions(
            'AdicionarPergunta'
        ).actions('edit', 'delete').template('adm/queryset/accordion')

    @meta('Quantidade de Perguntas')
    def get_quantidade_perguntas(self):
        return self.pergunta_set.count()

    @meta('Perguntas por Tipo')
    def get_quantidade_perguntas_por_tipo_resposta(self):
        return self.pergunta_set.count('tipo_resposta')


class OpcaoResposta(models.Model):
    nome = models.CharField(verbose_name='Resposta')

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
    ARQUIVO = 7
    OPCOES = 8

    TIPOS_RESPOSTA_CHOICES = [
        [1, 'Texto Curto'],
        [2, 'Texto Longo'],
        [3, 'Valor Monetário'],
        [4, 'Número Inteiro'],
        [5, 'Data'],
        [6, 'Sim/Não'],
        [7, 'Arquivo'],
        [8, 'Múltiplas Escolhas'],
    ]
    categoria = models.ForeignKey(Categoria, verbose_name='Categoria')
    texto = models.CharField(verbose_name='Texto')
    obrigatoria = models.BooleanField(verbose_name='Obrigatória', blank=True)
    tipo_resposta = models.IntegerField(verbose_name='Tipo de Resposta', choices=TIPOS_RESPOSTA_CHOICES)
    opcoes = models.OneToManyField(OpcaoResposta, verbose_name='Opções de Resposta', blank=True, max=5)

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for ciclo in Ciclo.objects.abertos():
            ciclo.gerar_questionarios()


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
        return self.gestor_set.list_display('nome', 'email').global_actions('AdicionarGestor').actions('edit', 'delete')


class Campus(models.Model):
    instituicao = models.ForeignKey(Instituicao, verbose_name='Campus')
    nome = models.CharField(verbose_name='Nome')

    class Meta:
        verbose_name = 'Campus'
        verbose_name_plural = 'Campi'

    def __str__(self):
        return '{}/{}'.format(self.nome, self.instituicao)


@role('Gestor', 'user', instituicao='instituicao')
class Gestor(models.Model):
    nome = models.CharField('Nome')
    email = models.CharField('E-mail', null=True)
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituição')

    user = models.ForeignKey(User, verbose_name='Usuário', blank=True)

    class Meta:
        verbose_name = 'Gestor '
        verbose_name_plural = 'Gestores'
        fieldsets = {
            'Dados Gerais': (('nome', 'email'), 'instituicao')
        }
        can_add = 'Administrador',
        can_edit = 'Administrador',
        can_delete = 'Administrador',

    def save(self, *args, **kwargs):
        if self.email:
            self.user = User.objects.get_or_create(
                username=self.email, defaults={}
            )[0]
            self.user.set_password('123')
            self.user.save()
        super().save()


class Notificacao(models.Model):
    descricao = models.CharField(verbose_name='Descrição')
    inicio = models.DateField(verbose_name='Início da Exibição')
    fim = models.DateField(verbose_name='Fim da Exibição')

    class Meta:
        icon = 'exclamation-square'
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        can_admin = 'Administrador',

    def __str__(self):
        return self.descricao


class DuvidaManager(models.Manager):
    @meta('Dúvidas')
    def all(self):
        return super().all().actions('ResponderDuvida')


class Duvida(models.Model):
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituicao', null=True)
    pergunta = models.TextField(verbose_name='Pergunta')
    data_pergunta = models.DateTimeField(verbose_name='Data da Pergunta')
    resposta = models.TextField(verbose_name='Resposta', null=True)
    data_resposta = models.DateTimeField(verbose_name='Data da Resposta', null=True)

    objects = DuvidaManager()

    class Meta:
        icon = 'question-square'
        verbose_name = 'Dúvida'
        verbose_name_plural = 'Dúvidas'
        can_list = 'Gestor', 'Administrador'
        can_add = 'Gestor',
        can_view = 'Gestor', 'Administrador'
        add_form = 'DuvidaForm'

    def __str__(self):
        return self.pergunta


class LimiteDemanda(models.Model):
    classificacao = models.ForeignKey(Categoria, verbose_name='Classificação')
    quantidade = models.PositiveIntegerField(verbose_name='Quantidade Máxima de Demandas')

    class Meta:
        verbose_name = 'Limite de Demanda'
        verbose_name_plural = 'Limites de Demanda'
        can_view = 'Gestor', 'Administrador'

    def __str__(self):
        return '{} - {} demandas'.format(self.classificacao, self.quantidade)


class CicloManager(models.Manager):
    @meta('Ciclos', roles=('Administrador',))
    def all(self):
        return super().all()

    @meta('Ciclos Abertos', roles=('Administrador',))
    def abertos(self):
        hoje = datetime.date.today()
        return super().filter(inicio__lte=hoje).exclude(fim__lt=datetime.date.today())


class Ciclo(models.Model):
    descricao = models.CharField(verbose_name='Descrição')
    inicio = models.DateField(verbose_name='Início das Solicitações')
    fim = models.DateField(verbose_name='Fim das Solicitações')
    teto = models.DecimalField(verbose_name='Limite de Investimento por Instituição (R$)', max_digits=15)
    instituicoes = models.ManyToManyField(Instituicao, verbose_name='Demandantes', blank=True, help_text='Não informar, caso deseje incluir todas as instituições.')
    limites = models.OneToManyField(LimiteDemanda, verbose_name='Limites de Demanda', max=5)

    objects = CicloManager()

    class Meta:
        icon = 'arrow-clockwise'
        verbose_name = 'Ciclo de Demandas'
        verbose_name_plural = 'Ciclos de Demandas'
        can_admin = 'Administrador',
        can_view = 'Gestor',
        can_list = 'Gestor',
        fieldsets = {
            'Dados Gerais': ('descricao', 'instituicoes'),
            'Período de Solicitação': (('inicio', 'fim'),),
            'Limite Financeiro': ('teto',),
        }

    def __str__(self):
        return self.descricao

    def is_aberto(self):
        hoje = datetime.date.today()
        return self.inicio >= hoje and self.fim <= hoje + timedelta(days=1)

    def gerar_demandas(self):
        for instituicao in self.instituicoes.all():
            for limite in self.limites.all():
                for i in range(1, limite.quantidade + 1):
                    prioridade = Prioridade.objects.get_or_create(numero=i)[0]
                    lookups = dict(ciclo=self, instituicao=instituicao, prioridade=prioridade, classificacao=limite.classificacao)
                    if not Demanda.objects.filter(**lookups).exists():
                        Demanda.objects.create(**lookups)

    def gerar_questionarios(self):
        for demanda in self.demanda_set.filter(classificacao__isnull=False):
            questionario = Questionario.objects.filter(demanda=demanda).first()
            if questionario is None:
                questionario = Questionario.objects.create(demanda=demanda)
            for pergunta in demanda.classificacao.pergunta_set.all():
                lookups = dict(questionario=questionario, pergunta=pergunta)
                if not RespostaQuestionario.objects.filter(**lookups).exists():
                    RespostaQuestionario.objects.create(**lookups)

    def post_save(self, *args, **kwargs):
        if not self.instituicoes.exists():
            for instituicao in Instituicao.objects.all():
                self.instituicoes.add(instituicao)
        self.gerar_demandas()
        self.gerar_questionarios()

    @meta('Limite de Demandas por Categoria')
    def get_limites_demandas(self):
        return self.limites.all()

    @meta('Total Solicitado por Categoria')
    def get_total_por_instituicao(self):
        return self.demanda_set.all().filter(valor__isnull=False).sum('valor', 'classificacao', 'instituicao')

    @meta('Solicitações')
    def get_solicitacoes(self):
        return self.demanda_set.all().list_filter('prioridade', 'classificacao').list_dynamic_filter('instituicao').order_by('prioridade__numero').ignore('ciclo').collapsed(False)

    @meta('Configuração Geral')
    def get_configuracao_geral(self):
        return self.values('teto', ('inicio', 'fim'))

    @meta('Configuração')
    def get_configuracao(self):
        return self.values('get_configuracao_geral', 'get_limites_demandas')

    @meta('Resumo')
    def get_resumo(self):
        return self.values('get_total_por_instituicao', 'get_questionario_final')

    @meta('Questionário Final')
    def get_questionario_final(self):
        return self.questionariofinal_set.all().list_display('rco_pendente', 'detalhe_rco_pendente', 'devolucao_ted', 'detalhe_devolucao_ted').role_lookups('Gestor', instituicao='instituicao')

    @meta('Detalhamento')
    def get_detalhamento(self):
        return self.values('get_solicitacoes', 'get_configuracao', 'get_resumo').actions('ConcluirSolicitacao')

    def view(self):
        return self.values('get_detalhamento')


class DemandaManager(models.Manager):
    @meta('Todas')
    def all(self):
        return self.list_display(
            'ciclo', 'instituicao', 'get_prioridade', 'get_dados_gerais', 'finalizada'
        ).attach(
            'aguardando_dados_gerais', 'aguardando_detalhamento', 'finalizadas'
        ).actions('AlterarPrioridade').role_lookups('Gestor', instituicao='instituicao')

    @meta('Aguardando Dados Gerais')
    def aguardando_dados_gerais(self):
        return self.list_display('ciclo', 'instituicao', 'get_prioridade', 'get_dados_gerais').filter(valor__isnull=True).actions(
            'PreencherDemanda', 'NaoInformarDemanda'
        ).role_lookups('Gestor', instituicao='instituicao')

    @meta('Aguardando Detalhamento')
    def aguardando_detalhamento(self):
        return self.list_display(
            'ciclo', 'instituicao', 'get_prioridade', 'get_dados_gerais', 'get_progresso_questionario'
        ).filter(valor__isnull=False, finalizada=False).actions(
            'DetalharDemanda', 'AlterarPreenchimento'
        ).role_lookups('Gestor', instituicao='instituicao')

    @meta('Preenchidas')
    def finalizadas(self):
        return self.filter(finalizada=True).actions('Reabir', 'AlterarDetalhamentoDemanda')


class Demanda(models.Model):
    ciclo = models.ForeignKey(Ciclo, verbose_name='Ciclo')
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituição')
    descricao = models.CharField(verbose_name='Descrição', max_length=512)
    prioridade = models.ForeignKey(Prioridade, verbose_name='Prioridade')
    classificacao = models.ForeignKey(Categoria, verbose_name='Categoria', null=True)
    valor_total = models.DecimalField(verbose_name='Valor Total (R$)', null=True)
    valor = models.DecimalField(verbose_name='Valor a Empenhar no Exercício (R$)', null=True)
    unidades_beneficiadas = models.ManyToManyField(Campus, verbose_name='Unidades Beneficiadas', blank=True,
                                                   help_text='Não informar caso todas as unidades sejam beneficiadas.')
    finalizada = models.BooleanField(verbose_name='Finalizada', default=False)

    objects = DemandaManager()

    class Meta:
        verbose_name = 'Demanda'
        verbose_name_plural = 'Demandas'
        can_view = 'Administrador', 'Gestor'

    def __str__(self):
        return self.descricao or 'Demanda {}'.format(self.pk)

    def get_questionario(self):
        return self.questionario_set.first()

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('descricao', 'valor_total', 'valor')

    @meta('Perguntas Obrigatórias')
    def get_total_perguntas(self):
        return self.get_questionario().respostaquestionario_set.filter(pergunta__obrigatoria=True).count() if self.get_questionario() else 0

    @meta('Total de Respostas')
    def get_total_respostas(self):
        return self.get_questionario().respostaquestionario_set.filter(pergunta__obrigatoria=True, resposta__isnull=False).count() if self.get_questionario() else 0

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
        return ['cb4335', 'ec7063', 'f1948a', 'f5b7b1', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8'][self.prioridade.numero-1]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.pk is None and self.classificacao:
            self.ciclo.gerar_questionarios()

    @meta('Resposta do Questionário')
    def get_respostas_questionario(self):
        return RespostaQuestionario.objects.filter(
            questionario__demanda=self
        ).list_display('pergunta', 'resposta').order_by('id')

    def view(self):
        return self.values('get_dados_gerais', 'get_respostas_questionario')


class Questionario(models.Model):
    demanda = models.ForeignKey(Demanda, verbose_name='Demanda')

    class Meta:
        verbose_name = 'Questionário'
        verbose_name_plural = 'Questionários'

    def __str__(self):
        return '{} - {}'.format(self.demanda.instituicao, self.demanda.ciclo)


class RespostaQuestionarioManager(models.Manager):
    @meta('Respostas')
    def all(self):
        return super().all().attach('aguardando_submissao', 'submetidas')

    @meta('Aguardando Submissão')
    def aguardando_submissao(self):
        return super().filter(resposta__isnull=True)

    @meta('Submetidas')
    def submetidas(self):
        return super().filter(resposta__isnull=False)


class RespostaQuestionario(models.Model):
    questionario = models.ForeignKey(Questionario, verbose_name='Questionário')
    pergunta = models.ForeignKey(Pergunta, verbose_name='Pergunta')
    resposta = models.TextField(verbose_name='Resposta', null=True)

    objects = RespostaQuestionarioManager()

    class Meta:
        icon = 'pencil-square'
        verbose_name = 'Resposta de Questionário'
        verbose_name_plural = 'Respostas dos Questionário'
        can_list = 'Administrador',
        list_display = 'get_ciclo', 'get_instituicao', 'get_categoria_demanda', 'get_prioridade_demanda', 'get_demanda', 'pergunta', 'resposta'
        list_filter = 'questionario__demanda__instituicao', 'questionario__demanda__ciclo'

    @meta('Demanda')
    def get_demanda(self):
        return self.questionario.demanda.descricao

    @meta('Classificação')
    def get_categoria_demanda(self):
        return self.questionario.demanda.classificacao

    @meta('Prioridade')
    def get_prioridade_demanda(self):
        return self.questionario.demanda.prioridade

    @meta('Ciclo')
    def get_ciclo(self):
        return self.questionario.demanda.ciclo

    @meta('Instituição')
    def get_instituicao(self):
        return self.questionario.demanda.instituicao

    def __str__(self):
        return '{} - {}'.format(self.pergunta, self.resposta)


class Anexo(models.Model):
    descricao = models.CharField(verbose_name='Descrição')
    arquivo = models.FileField(verbose_name='Arquivo', upload_to='anexos')

    class Meta:
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'

    def __str__(self):
        return self.descricao


class Mensagem(models.Model):
    perfil = models.CharField(verbose_name='Perfil', choices=[['Administrador', 'Administrador'], ['Gestor', 'Gestor']])
    introducao = models.TextField(verbose_name='Introdução')
    detalhamento = models.TextField(verbose_name='Detalhamento')
    anexos = models.OneToManyField(Anexo, verbose_name='Anexos')

    class Meta:
        icon = 'chat-left-text'
        verbose_name = 'Mensagem Inicial'
        verbose_name_plural = 'Mensagens Iniciais'
        can_list = 'Administrador',
        can_edit = 'Administrador',

    def __str__(self):
        return self.introducao

    def can_add(self, user):
        return Mensagem.objects.count() < 2


class QuestionarioFinal(models.Model):

    ciclo = models.ForeignKey(Ciclo, verbose_name='Ciclo')
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituição')
    rco_pendente = models.CharField(
        verbose_name='RCO Pendente',
        choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']],
    )
    detalhe_rco_pendente = models.TextField(
        verbose_name='Detalhe de RCO Pendente',
        null=True, blank=True
    )
    devolucao_ted = models.CharField(
        verbose_name='Devolução de TED',
        choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']],
    )
    detalhe_devolucao_ted = models.TextField(
        verbose_name='Detalhe de Devolução de TED',
        null=True, blank=True
    )
    finalizado = models.BooleanField(verbose_name='Finalizado', default=False)

    class Meta:
        verbose_name = 'Questionário Final'
        verbose_name_plural = 'Questionários Finais'
        can_view = 'Administrador', 'Gestor'

    def __str__(self):
        return 'Questionário final'
