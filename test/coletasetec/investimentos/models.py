# -*- coding: utf-8 -*-
import datetime
from django.core.mail import send_mail
from django.contrib.auth.models import User
from sloth.db import models, role, meta


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


class CategoriaManager(models.Manager):
    def all(self):
        return self.role_lookups('Administrador').display('nome', 'cor', 'get_quantidade_perguntas')


class Categoria(models.Model):
    nome = models.CharField(verbose_name='Nome')
    cor = models.ColorField(verbose_name='Cor', default='#FFFFFF')
    contabilizar = models.BooleanField('Contabilizar', default=True, help_text='Debitar no limite de investimento quando uma solicitação for realizada.')

    objects = CategoriaManager()

    class Meta:
        icon = 'folder'
        verbose_name = 'Categoria de Investimento'
        verbose_name_plural = 'Categorias de Investimento'

    def __str__(self):
        return self.nome

    def view(self):
        return self.value_set('get_dados_gerais', 'get_perguntas').append('get_quantidade_perguntas_por_tipo_resposta')

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.value_set('nome')

    @meta('Questionário')
    def get_perguntas(self):
        return self.pergunta_set.all().ignore('categoria').global_actions(
            'AdicionarPergunta'
        ).order_by('ordem').actions('editar_pergunta', 'delete', 'reordenar_pergunta')#.accordion()

    @meta('Quantidade de Perguntas')
    def get_quantidade_perguntas(self):
        return self.pergunta_set.count()

    @meta('Perguntas por Tipo')
    def get_quantidade_perguntas_por_tipo_resposta(self):
        return self.pergunta_set.count('tipo_resposta').donut_chart()

    def has_permission(self, user):
        return user.roles.contains('Administrador')

class OpcaoResposta(models.Model):
    nome = models.CharField(verbose_name='Resposta')

    class Meta:
        verbose_name = 'Opção de Resposta'
        verbose_name_plural = 'Opções de Resposta'

    def __str__(self):
        return self.nome


class PerguntaManager(models.Manager):
    def all(self):
        return self.display('categoria', 'texto', 'obrigatoria', 'get_tipo_resposta')


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

    def __str__(self):
        ordem = '{}) '.format(self.ordem) if self.ordem else ''
        return '{}{}'.format(ordem, self.texto)

    @meta('Tipo de Resposta')
    def get_tipo_resposta(self):
        return self.get_tipo_resposta_display()

    def has_permission(self, user):
        return user.roles.contains('Administrador')

    def save(self, *args, **kwargs):
        if self.ordem is None:
            self.ordem = self.categoria.pergunta_set.count() + 1
        super().save(*args, **kwargs)


class InstituicaoManager(models.Manager):
    def all(self):
        return self.role_lookups('Administrador')


class Instituicao(models.Model):
    nome = models.CharField(verbose_name='Nome')
    sigla = models.CharField(verbose_name='Sigla')

    objects = InstituicaoManager()

    class Meta:
        icon = 'building'
        verbose_name = 'Instituição'
        verbose_name_plural = 'Instituições'

    def __str__(self):
        return self.sigla

    def view(self):
        return self.value_set('get_dados_gerais', 'get_gestores', 'get_campi')

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.value_set('nome', 'sigla')

    @meta('Campi')
    def get_campi(self):
        return self.campus_set.ignore('instituicao').global_actions('AdicionarCampus').actions('editar_campus', 'delete')

    @meta('Gestores')
    def get_gestores(self):
        return self.gestor_set.display('nome', 'email').global_actions('AdicionarGestor').actions('editar_email_gestor', 'delete')

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class Campus(models.Model):
    instituicao = models.ForeignKey(Instituicao, verbose_name='Campus')
    nome = models.CharField(verbose_name='Nome')

    class Meta:
        verbose_name = 'Campus'
        verbose_name_plural = 'Campi'

    def __str__(self):
        return '{}/{}'.format(self.nome, self.instituicao)


class GestorManager(models.Manager):
    def all(self):
        return self.role_lookups('Administrador').global_actions('enviar_senhas').batch_actions('enviar_senhas')


@role('Gestor', username='email', instituicao='instituicao')
class Gestor(models.Model):
    nome = models.CharField('Nome')
    email = models.CharField('E-mail', null=True)
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituição')
    notificado = models.BooleanField('Notificado', default=False)

    objects = GestorManager()

    class Meta:
        verbose_name = 'Gestor '
        verbose_name_plural = 'Gestores'
        fieldsets = {
            'Dados Gerais': (('nome', 'email'), 'instituicao')
        }


class NotificacaoManager(models.Manager):
    def all(self):
        return self.role_lookups('Gestor', 'Administrador')

    def ativas(self):
        return self.filter(inicio__lte=datetime.date.today(), inicio__gte=datetime.date.today())


class Notificacao(models.Model):
    descricao = models.CharField(verbose_name='Descrição')
    inicio = models.DateField(verbose_name='Início da Exibição')
    fim = models.DateField(verbose_name='Fim da Exibição')

    objects = NotificacaoManager()

    class Meta:
        icon = 'exclamation-square'
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'

    def __str__(self):
        return self.descricao

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class LimiteDemanda(models.Model):
    classificacao = models.ForeignKey(Categoria, verbose_name='Classificação')
    quantidade = models.PositiveIntegerField(verbose_name='Quantidade Máxima de Demandas')

    class Meta:
        verbose_name = 'Limite de Demanda'
        verbose_name_plural = 'Limites de Demanda'

    def __str__(self):
        return '{} - {} demandas'.format(self.classificacao, self.quantidade)


class CicloManager(models.Manager):
    @meta('Ciclos')
    def all(self):
        return self.role_lookups('Administrador')

    @meta('Ciclos Abertos')
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
            'Limite de Demandas': ('limites',),
        }

    def has_permission(self, user):
        return user.roles.contains('Administrador')

    def __str__(self):
        return self.descricao

    def is_aberto(self):
        hoje = datetime.date.today()
        return self.inicio <= hoje and self.fim >= hoje

    def post_save(self, *args, **kwargs):
        super().post_save(*args, **kwargs)
        if not self.instituicoes.exists():
            for instituicao in Instituicao.objects.all():
                self.instituicoes.add(instituicao)

        for instituicao in self.instituicoes.all():
            if not Solicitacao.objects.filter(instituicao=instituicao, ciclo=self).exists():
                Solicitacao.objects.create(instituicao=instituicao, ciclo=self)

    @meta('Limite de Demandas por Categoria')
    def get_limites_demandas(self):
        return self.limites.all()

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.value_set('teto', ('inicio', 'fim'))

    @meta('Solicitantes')
    def get_solicitantes(self):
        return self.solicitacao_set.all().ignore('ciclo').actions('view').expand()

    @meta('Demandas Solicitadas')
    def get_demandas(self):
        return Demanda.objects.filter(solicitacao__ciclo=self).ignore('solicitacao').all().expand().actions('visualizar_questionario')

    @meta('Total Solicitado por Categoria')
    def get_total_por_instituicao(self):
        return Demanda.objects.filter(
            solicitacao__ciclo=self,
        ).filter(valor__isnull=False).sum('valor', 'classificacao', 'solicitacao__instituicao')

    def get_detalhamento(self):
        return self.value_set('get_solicitantes', 'get_total_por_instituicao', 'get_demandas')

    def view(self):
        return self.value_set('get_dados_gerais', 'get_detalhamento').actions('exportar_resultado', 'exportar_resultado_por_categoria')


class SolicitacaoManager(models.Manager):
    def all(self):
        return self.display('ciclo', 'ciclo__teto', 'instituicao', 'get_total_demandas', 'get_total_solicitado', 'get_percentual_solicitado', 'is_finalizada').role_lookups('Administrador').role_lookups('Gestor', instituicao='instituicao')


class Solicitacao(models.Model):
    ciclo = models.ForeignKey(Ciclo, verbose_name='Ciclo')
    instituicao = models.ForeignKey(Instituicao, verbose_name='Instituição')

    objects = SolicitacaoManager()

    class Meta:
        verbose_name = 'Solicitação'
        verbose_name_plural = 'Solicitações'

    def __str__(self):
        return '{} - {}'.format(self.ciclo, self.instituicao)

    @meta('Finalizada', renderer='badges/boolean')
    def is_finalizada(self):
        return self.questionariofinal_set.filter(finalizado=True).exists()

    @meta('Demandas Permitidas por Categoria')
    def get_qtd_demandas_permitidas(self):
        return self.ciclo.limites.sum('quantidade', 'classificacao')

    def get_total_solicitado(self):
        return self.demanda_set.filter(classificacao__contabilizar=True).sum('valor')

    @meta('Percentual solicitado', renderer='utils/progress')
    def get_percentual_solicitado(self):
        return int(self.get_total_solicitado()*100/self.ciclo.teto)

    def get_total_demandas(self):
        return self.demanda_set.count()

    @meta('Total Solicitado por Categoria')
    def get_total_por_categoria(self):
        return self.demanda_set.all().filter(valor__isnull=False).sum('valor', 'classificacao')

    @meta('Demandas')
    def get_demandas(self):
        return self.demanda_set.all().filters('prioridade', 'classificacao').order_by('prioridade__numero').ignore('ciclo').collapsed(False).global_actions('adicionar_demanda', 'concluir_solicitacao').totalizer('valor').ordering('prioridade', 'classificacao').actions('visualizar_questionario')

    @meta('Início')
    def get_inicio(self):
        return self.ciclo.inicio

    @meta('Fim')
    def get_fim(self):
        return self.ciclo.fim

    @meta('Limite Orçamentário')
    def get_limite_orcamentario(self):
        return self.ciclo.teto

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.value_set(('get_inicio', 'get_fim'), ('get_limite_orcamentario', 'get_total_solicitado'))

    @meta('Resumo')
    def get_resumo(self):
        return self.value_set('get_total_por_categoria', 'get_questionario_final')

    @meta('Questionário Final')
    def get_questionario_final(self):
        questionario_final = self.questionariofinal_set.first()
        return self.questionariofinal_set.first().value_set('rco_pendente', 'detalhe_rco_pendente', 'devolucao_ted', 'detalhe_devolucao_ted', 'prioridade_1', 'prioridade_2', 'prioridade_3') if questionario_final else None

    @meta('Detalhamento')
    def get_detalhamento(self):
        return self.value_set('get_demandas', 'get_resumo')

    def view(self):
        return self.value_set('get_dados_gerais', 'get_percentual_solicitado', 'get_qtd_demandas_permitidas', 'get_detalhamento')

    def has_view_permission(self, user):
        return user.roles.contains('Administrador', 'Gestor')


class DemandaManager(models.Manager):
    @meta('Todas')
    def all(self):
        return self.display(
            'get_prioridade', 'get_dados_gerais', 'get_categoria', 'get_progresso_questionario', 'is_finalizada'
        ).attach(
            'aguardando_detalhamento', 'finalizadas'
        ).role_lookups('Gestor', solicitacao__instituicao='instituicao')

    @meta('Aguardando Detalhamento')
    def aguardando_detalhamento(self):
        return self.filter(valor__isnull=False, finalizada=False).display(
            'get_prioridade', 'get_dados_gerais', 'get_categoria', 'get_progresso_questionario', 'is_finalizada'
        ).actions(
            'alterar_demanda', 'detalhar_demanda', 'alterar_prioridade'
        ).role_lookups('Gestor', solicitacao__instituicao='instituicao')

    @meta('Preenchidas')
    def finalizadas(self):
        return self.filter(finalizada=True).actions('reabrir')


class Demanda(models.Model):
    solicitacao = models.ForeignKey(Solicitacao, verbose_name='Solicitação', null=True)
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

    def __str__(self):
        return self.descricao or 'Demanda {}'.format(self.pk)

    def get_questionario(self):
        questionario = self.questionario_set.first()
        if questionario is None:
            questionario = Questionario.objects.create(demanda=self)
            for pergunta in self.classificacao.pergunta_set.all():
                lookups = dict(questionario=questionario, pergunta=pergunta)
                if not RespostaQuestionario.objects.filter(**lookups).exists():
                    RespostaQuestionario.objects.create(**lookups)
        return questionario

    @meta('Dados Gerais')
    def get_dados_gerais(self):
        return self.value_set('descricao', 'valor_total', 'valor')

    @meta('Perguntas Obrigatórias')
    def get_total_perguntas(self):
        return self.get_questionario().respostaquestionario_set.filter(pergunta__obrigatoria=True).count() if self.get_questionario() else 0

    @meta('Total de Respostas')
    def get_total_respostas(self):
        return self.get_questionario().respostaquestionario_set.filter(pergunta__obrigatoria=True, resposta__isnull=False).count() if self.get_questionario() else 0

    @meta('Questionário')
    def get_dados_questionario(self):
        return self.value_set('get_total_perguntas', 'get_total_respostas', 'get_progresso_questionario')

    @meta('Respostas do Questionário', 'utils/progress')
    def get_progresso_questionario(self):
        total_perguntas = self.get_total_perguntas()
        total_respostas = self.get_total_respostas()
        if total_perguntas:
            return int(total_respostas * 100 / total_perguntas)
        return 0

    @meta('Categoria', renderer='badges/badge')
    def get_categoria(self):
        return self.classificacao.cor, self.classificacao.nome

    @meta('Prioridade', renderer='prioridade')
    def get_prioridade(self):
        return self.prioridade

    def get_cor(self):
        return ['cb4335', 'ec7063', 'f1948a', 'f5b7b1', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8', 'fadbd8'][self.prioridade.numero-1]

    @meta('Finalizada')
    def is_finalizada(self):
        return self.finalizada

    @meta('Resposta do Questionário')
    def get_respostas_questionario(self):
        return RespostaQuestionario.objects.filter(
            questionario__demanda=self
        ).display('pergunta', 'resposta').order_by('id').renderer('respostas_questionario.html')

    def view(self):
        return self.value_set('get_dados_gerais', 'get_respostas_questionario')

    def has_view_permission(self, user):
        return user.roles.contains('Gestor', 'Administrador')


class Questionario(models.Model):
    demanda = models.ForeignKey(Demanda, verbose_name='Demanda')

    class Meta:
        verbose_name = 'Questionário'
        verbose_name_plural = 'Questionários'

    def __str__(self):
        return '{} - {}'.format(self.demanda.solicitacao.instituicao, self.demanda.solicitacao.ciclo)


class RespostaQuestionarioManager(models.Manager):
    @meta('Respostas')
    def all(self):
        return self.display(
            'get_ciclo', 'get_instituicao', 'get_categoria_demanda', 'get_prioridade_demanda', 'get_demanda', 'pergunta', 'resposta'
        ).filters(
            'questionario__demanda__instituicao', 'questionario__demanda__ciclo'
        ).attach(
            'aguardando_submissao', 'submetidas'
        )

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
        verbose_name_plural = 'Respostas dos Questionários'

    @meta('Demanda')
    def get_demanda(self):
        return self.questionario.demanda.descricao

    @meta('Classificação')
    def get_categoria_demanda(self):
        return self.questionario.demanda.classificacao

    @meta('Prioridade', renderer='prioridade')
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


class AnexoManager(models.Manager):
    def all(self):
        return self.display('descricao', 'get_arquivo').role_lookups('Administrador')


class Anexo(models.Model):
    descricao = models.CharField(verbose_name='Descrição')
    arquivo = models.FileField(verbose_name='Arquivo', upload_to='anexos')

    objects = AnexoManager()

    class Meta:
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'

    def __str__(self):
        return self.descricao

    @meta('Arquivo', renderer='links/file')
    def get_arquivo(self):
        return self.arquivo


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

    def __str__(self):
        return self.introducao

    def has_add_permission(self, user):
        return Mensagem.objects.count() < 2


class QuestionarioFinal(models.Model):
    solicitacao = models.ForeignKey(Solicitacao, verbose_name='Solicitação', null=True)
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
    prioridade_4 = models.ForeignKey(Demanda, verbose_name='Prioridade 4', null=True, blank=True, related_name='r4')
    prioridade_5 = models.ForeignKey(Demanda, verbose_name='Prioridade 5', null=True, blank=True, related_name='r5')

    finalizado = models.BooleanField(verbose_name='Finalizado', default=False)

    class Meta:
        verbose_name = 'Questionário Final'
        verbose_name_plural = 'Questionários Finais'

    def __str__(self):
        return 'Questionário final'


class DuvidaManager(models.Manager):
    @meta('Dúvidas')
    def all(self):
        return self.role_lookups('Administrador').role_lookups('Gestor', instituicao='instituicao').actions('responder_duvida').global_actions('cadastrar_duvida')

    def nao_respondidas(self):
        return self.filter(data_resposta__isnull=True)


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
