# -*- coding: utf-8 -*-
import datetime
from datetime import timedelta
from django.core.mail import send_mail
from django.contrib.auth.models import User
from sloth.db import models, verbose_name, role


@role('Administrador', username='cpf')
class Administrador(models.Model):
    nome = models.CharField('Nome')
    cpf = models.CharField('CPF', rmask='000.000.000-00')

    class Meta:
        icon = 'person-workspace'
        verbose_name = 'Administrador'
        verbose_name_plural = 'Administradores'
        fieldsets = {
            'Dados Gerais': ('nome', 'cpf')
        }

    def __str__(self):
        return self.nome


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
    contabilizar = models.BooleanField('Contatilizar', default=True, help_text='Debitar no limite de investimento quando uma solicitação for realizada.')

    class Meta:
        icon = 'folder'
        verbose_name = 'Categoria de Investimento'
        verbose_name_plural = 'Categorias de Investimento'
        list_display = 'nome', 'get_quantidade_perguntas'

    class Permission:
        admin = 'Administrador',

    def __str__(self):
        return self.nome

    def view(self):
        return self.values('get_dados_gerais', 'get_perguntas').append('get_quantidade_perguntas_por_tipo_resposta')

    @verbose_name('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('nome')

    @verbose_name('Questionário')
    def get_perguntas(self):
        return self.pergunta_set.all().ignore('categoria').global_actions(
            'AdicionarPergunta'
        ).order_by('ordem').actions('edit', 'delete').template('adm/queryset/accordion')

    @verbose_name('Quantidade de Perguntas')
    def get_quantidade_perguntas(self):
        return self.pergunta_set.count()

    @verbose_name('Perguntas por Tipo')
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
    ordem = models.IntegerField(verbose_name='Ordem', null=True)
    texto = models.CharField(verbose_name='Texto')
    obrigatoria = models.BooleanField(verbose_name='Obrigatória', blank=True)
    tipo_resposta = models.IntegerField(verbose_name='Tipo de Resposta', choices=TIPOS_RESPOSTA_CHOICES)
    opcoes = models.OneToManyField(OpcaoResposta, verbose_name='Opções de Resposta', blank=True, max=10)

    class Meta:
        verbose_name = 'Pergunta'
        verbose_name_plural = 'Perguntas'
        list_display = 'categoria', 'texto', 'obrigatoria', 'get_tipo_resposta'

    class Permission:
        delete = 'Administrador',
        edit = 'Administrador',

    def __str__(self):
        ordem = '{}) '.format(self.ordem) if self.ordem else ''
        return '{}{}'.format(ordem, self.texto)

    @verbose_name('Tipo de Resposta')
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
        icon = 'building'
        verbose_name = 'Instituição'
        verbose_name_plural = 'Instituições'

    class Permission:
        admin = 'Administrador',

    def __str__(self):
        return self.sigla

    def view(self):
        return self.values('get_dados_gerais', 'get_gestores', 'get_campi')

    @verbose_name('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('nome', 'sigla')

    @verbose_name('Campi')
    def get_campi(self):
        return self.campus_set.ignore('instituicao').global_actions('AdicionarCampus').actions('edit', 'delete')

    @verbose_name('Gestores')
    def get_gestores(self):
        return self.gestor_set.display('nome', 'email').global_actions('AdicionarGestor').actions('edit', 'delete')


class Campus(models.Model):
    instituicao = models.ForeignKey(Instituicao, verbose_name='Campus')
    nome = models.CharField(verbose_name='Nome')

    class Meta:
        verbose_name = 'Campus'
        verbose_name_plural = 'Campi'

    def __str__(self):
        return '{}/{}'.format(self.nome, self.instituicao)


@role('Gestor', username='email', instituicao='instituicao')
class Gestor(models.Model):
    nome = models.CharField('Nome')
    email = models.CharField('E-mail', null=True)
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituição')

    class Meta:
        verbose_name = 'Gestor '
        verbose_name_plural = 'Gestores'
        fieldsets = {
            'Dados Gerais': (('nome', 'email'), 'instituicao')
        }

    class Permission:
        add = 'Administrador',
        edit = 'Administrador',
        delete = 'Administrador',


class Notificacao(models.Model):
    descricao = models.CharField(verbose_name='Descrição')
    inicio = models.DateField(verbose_name='Início da Exibição')
    fim = models.DateField(verbose_name='Fim da Exibição')

    class Meta:
        icon = 'exclamation-square'
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'

    class Permission:
        admin = 'Administrador',

    def __str__(self):
        return self.descricao


class LimiteDemanda(models.Model):
    classificacao = models.ForeignKey(Categoria, verbose_name='Classificação')
    quantidade = models.PositiveIntegerField(verbose_name='Quantidade Máxima de Demandas')

    class Meta:
        verbose_name = 'Limite de Demanda'
        verbose_name_plural = 'Limites de Demanda'

    class Permission:
        view = 'Gestor', 'Administrador'

    def __str__(self):
        return '{} - {} demandas'.format(self.classificacao, self.quantidade)


class CicloManager(models.Manager):
    @verbose_name('Ciclos')
    def all(self):
        return super().role_lookups('Gestor', instituicao='instituicoes')

    @verbose_name('Ciclos Abertos')
    def abertos(self):
        hoje = datetime.date.today()
        return super().filter(inicio__lte=hoje).exclude(fim__lt=datetime.date.today())


class Ciclo(models.Model):
    descricao = models.CharField(verbose_name='Descrição')
    inicio = models.DateField(verbose_name='Início das Solicitações')
    fim = models.DateField(verbose_name='Fim das Solicitações')
    teto = models.DecimalField(verbose_name='Limite Orçamentário (R$)', max_digits=15)
    instituicoes = models.ManyToManyField(Instituicao, verbose_name='Demandantes', blank=True, help_text='Não informar, caso deseje incluir todas as instituições.')
    limites = models.OneToManyField(LimiteDemanda, verbose_name='Limites de Demanda', max=10)

    objects = CicloManager()

    class Meta:
        icon = 'arrow-clockwise'
        verbose_name = 'Ciclo de Demandas'
        verbose_name_plural = 'Ciclos de Demandas'
        fieldsets = {
            'Dados Gerais': ('descricao', 'instituicoes'),
            'Período de Solicitação': (('inicio', 'fim'),),
            'Limite Financeiro': ('teto',),
        }

    class Permission:
        admin = 'Administrador',
        view = 'Gestor',
        list = 'Gestor',

    def __str__(self):
        return self.descricao

    def is_aberto(self):
        hoje = datetime.date.today()
        return self.inicio <= hoje and self.fim >= hoje

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

    @verbose_name('Limite de Demandas por Categoria')
    def get_limites_demandas(self):
        return self.limites.all()

    @verbose_name('Total Solicitado por Categoria')
    def get_total_por_instituicao(self):
        return self.demanda_set.all().filter(valor__isnull=False).sum('valor', 'classificacao', 'instituicao')

    @verbose_name('Solicitações')
    def get_solicitacoes(self):
        return self.demanda_set.all().filters('prioridade', 'classificacao').dynamic_filters('instituicao').order_by('prioridade__numero').ignore('ciclo').collapsed(False).role_lookups('Gestor', instituicao='instituicao')

    @verbose_name('Configuração Geral')
    def get_configuracao_geral(self):
        return self.values('teto', ('inicio', 'fim'))

    def has_get_configuracao_permission(self, user):
        return user.is_superuser or user.roles.contains('Administrador')

    @verbose_name('Configuração')
    def get_configuracao(self):
        return self.values('get_configuracao_geral', 'get_limites_demandas')

    @verbose_name('Resumo')
    def get_resumo(self):
        return self.values('get_total_por_instituicao', 'get_questionario_final')

    @verbose_name('Questionário Final')
    def get_questionario_final(self):
        return self.questionariofinal_set.all().display('instituicao', 'rco_pendente', 'detalhe_rco_pendente', 'devolucao_ted', 'detalhe_devolucao_ted', 'prioridade_1', 'prioridade_2', 'prioridade_3').role_lookups('Gestor', instituicao='instituicao')

    @verbose_name('Detalhamento')
    def get_detalhamento(self):
        return self.values('get_solicitacoes', 'get_configuracao', 'get_resumo').actions('ConcluirSolicitacao', 'ExportarResultado', 'ExportarResultadoPorCategoria')

    def view(self):
        return self.values('get_configuracao_geral', 'get_detalhamento')


class DemandaManager(models.Manager):
    @verbose_name('Todas')
    def all(self):
        return self.display(
            'ciclo', 'instituicao', 'get_prioridade', 'get_dados_gerais', 'finalizada'
        ).attach(
            'aguardando_dados_gerais', 'aguardando_detalhamento', 'finalizadas'
        ).actions('AlterarPrioridade').role_lookups('Gestor', instituicao='instituicao')

    @verbose_name('Aguardando Dados Gerais')
    def aguardando_dados_gerais(self):
        return self.display('ciclo', 'instituicao', 'get_prioridade', 'get_dados_gerais').filter(valor__isnull=True).actions(
            'PreencherDemanda', 'NaoInformarDemanda'
        ).role_lookups('Gestor', instituicao='instituicao')

    @verbose_name('Aguardando Detalhamento')
    def aguardando_detalhamento(self):
        return self.display(
            'ciclo', 'instituicao', 'get_prioridade', 'get_dados_gerais', 'get_progresso_questionario'
        ).filter(valor__isnull=False, finalizada=False).actions(
            'DetalharDemanda', 'AlterarPreenchimento', 'RestaurarDemanda'
        ).role_lookups('Gestor', instituicao='instituicao').view('get_dados_gerais')

    @verbose_name('Preenchidas')
    def finalizadas(self):
        return self.filter(finalizada=True).actions('Reabir', 'AlterarDetalhamentoDemanda')


class Demanda(models.Model):
    ciclo = models.ForeignKey(Ciclo, verbose_name='Ciclo')
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituição')
    descricao = models.CharField(verbose_name='Descrição', max_length=512)
    prioridade = models.ForeignKey(Prioridade, verbose_name='Prioridade')
    classificacao = models.ForeignKey(Categoria, verbose_name='Categoria', null=True)
    valor_total = models.DecimalField(verbose_name='Valor Total (R$)', null=True, max_digits=15)
    valor = models.DecimalField(verbose_name='Valor a Empenhar no Exercício (R$)', null=True, max_digits=15)
    unidades_beneficiadas = models.ManyToManyField(Campus, verbose_name='Unidades Beneficiadas', blank=True,
                                                   help_text='Não informar caso todas as unidades sejam beneficiadas.')
    finalizada = models.BooleanField(verbose_name='Finalizada', default=False)

    objects = DemandaManager()

    class Meta:
        verbose_name = 'Demanda'
        verbose_name_plural = 'Demandas'

    class Permission:
        view = 'Administrador', 'Gestor'

    def __str__(self):
        return self.descricao or 'Demanda {}'.format(self.pk)

    def get_questionario(self):
        return self.questionario_set.first()

    @verbose_name('Dados Gerais')
    def get_dados_gerais(self):
        return self.values('descricao', 'valor_total', 'valor')

    @verbose_name('Perguntas Obrigatórias')
    def get_total_perguntas(self):
        return self.get_questionario().respostaquestionario_set.filter(pergunta__obrigatoria=True).count() if self.get_questionario() else 0

    @verbose_name('Total de Respostas')
    def get_total_respostas(self):
        return self.get_questionario().respostaquestionario_set.filter(pergunta__obrigatoria=True, resposta__isnull=False).count() if self.get_questionario() else 0

    @verbose_name('Questionário')
    def get_dados_questionario(self):
        return self.values('get_total_perguntas', 'get_total_respostas', 'get_progresso_questionario')

    @verbose_name('Respostas do Questionário', template='adm/formatters/progress')
    def get_progresso_questionario(self):
        total_perguntas = self.get_total_perguntas()
        total_respostas = self.get_total_respostas()
        if total_perguntas:
            return int(total_respostas * 100 / total_perguntas)
        return 0

    @verbose_name('Prioridade', template='prioridade')
    def get_prioridade(self):
        return self.prioridade

    def get_cor(self):
        return ['cb4335', 'ec7063', 'f1948a', 'f5b7b1', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8'][self.prioridade.numero-1]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.pk is None and self.classificacao:
            self.ciclo.gerar_questionarios()

    @verbose_name('Resposta do Questionário')
    def get_respostas_questionario(self):
        return RespostaQuestionario.objects.filter(
            questionario__demanda=self
        ).display('pergunta', 'resposta').order_by('id').template('respostas_questionario.html')

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
    @verbose_name('Respostas')
    def all(self):
        return super().all().attach('aguardando_submissao', 'submetidas')

    @verbose_name('Aguardando Submissão')
    def aguardando_submissao(self):
        return super().filter(resposta__isnull=True)

    @verbose_name('Submetidas')
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
        verbose_name_plural = 'Respostas dos Questionários'
        list_display = 'get_ciclo', 'get_instituicao', 'get_categoria_demanda', 'get_prioridade_demanda', 'get_demanda', 'pergunta', 'resposta'
        list_filter = 'questionario__demanda__instituicao', 'questionario__demanda__ciclo'

    class Permission:
        view = 'Administrador', 'Gestor'

    @verbose_name('Demanda')
    def get_demanda(self):
        return self.questionario.demanda.descricao

    @verbose_name('Classificação')
    def get_categoria_demanda(self):
        return self.questionario.demanda.classificacao

    @verbose_name('Prioridade')
    def get_prioridade_demanda(self):
        return self.questionario.demanda.prioridade

    @verbose_name('Ciclo')
    def get_ciclo(self):
        return self.questionario.demanda.ciclo

    @verbose_name('Instituição')
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

    notificados = models.ManyToManyField(User, verbose_name='Notificados', blank=True)

    class Meta:
        icon = 'chat-left-text'
        verbose_name = 'Mensagem Inicial'
        verbose_name_plural = 'Mensagens Iniciais'

    class Permission:
        list = 'Administrador',
        edit = 'Administrador',

    def __str__(self):
        return self.introducao

    def has_add_permission(self, user):
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
    prioridade_1 = models.ForeignKey(Demanda, verbose_name='Prioridade 1', null=True, blank=True, related_name='r1')
    prioridade_2 = models.ForeignKey(Demanda, verbose_name='Prioridade 2', null=True, blank=True, related_name='r2')
    prioridade_3 = models.ForeignKey(Demanda, verbose_name='Prioridade 3', null=True, blank=True, related_name='r3')

    finalizado = models.BooleanField(verbose_name='Finalizado', default=False)

    class Meta:
        verbose_name = 'Questionário Final'
        verbose_name_plural = 'Questionários Finais'

    class Permission:
        view = 'Administrador', 'Gestor'

    def __str__(self):
        return 'Questionário final'


class DuvidaManager(models.Manager):
    @verbose_name('Dúvidas')
    def all(self):
        return super().all().actions('ResponderDuvida').role_lookups('Gestor', instituicao='instituicao')


class Duvida(models.Model):
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituição', null=True)
    pergunta = models.TextField(verbose_name='Pergunta')
    data_pergunta = models.DateTimeField(verbose_name='Data da Pergunta')
    resposta = models.TextField(verbose_name='Resposta', null=True)
    data_resposta = models.DateTimeField(verbose_name='Data da Resposta', null=True)

    objects = DuvidaManager()

    class Meta:
        icon = 'question-square'
        verbose_name = 'Dúvida'
        verbose_name_plural = 'Dúvidas'
        add_form = 'DuvidaForm'

    class Permission:
        list = 'Gestor', 'Administrador'
        add = 'Gestor',
        view = 'Gestor', 'Administrador'

    def __str__(self):
        return self.pergunta

    def save(self, *args, **kwargs):
        if not self.pk:
            send_mail(
                'COLETA SETEC - Dúvida',
                'Nova dúvida cadastrada [{}]: \n{}.'.format(self.instituicao, self.pergunta),
                'naoresponder.ifrn.edu.br',
                ['cgpgsetec@mec.gov.br'],
                fail_silently=False,
            )
        super().save(*args, **kwargs)
