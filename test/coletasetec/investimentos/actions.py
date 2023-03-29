# -*- coding: utf-8 -*-
import os
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from sloth import actions
from sloth.utils.formatter import format_value
from sloth.utils.http import XlsResponse
from .mail import enviar_senha
from .models import Campus, Demanda, Pergunta, Gestor, QuestionarioFinal, Duvida, Instituicao, Categoria, Prioridade


class AdicionarGestor(actions.Action):
    class Meta:
        model = Gestor
        fields = 'nome', 'email'
        verbose_name = 'Adicionar Gestor'
        related_field = 'instituicao'

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class AdicionarPergunta(actions.Action):
    class Meta:
        model = Pergunta
        verbose_name = 'Adicionar Pergunta'
        related_field = 'categoria'
        fieldsets = {
            'Dados Gerais': ('ordem', 'texto', 'tipo_resposta', 'obrigatoria'),
            'Opções de Resposta': ('opcoes',)
        }

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class AdicionarCampus(actions.Action):
    class Meta:
        model = Campus
        fields = 'nome',
        verbose_name = 'Adicionar Campus'
        related_field = 'instituicao'

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class AlterarPrioridade(actions.Action):
    class Meta:
        style = 'warning'
        model = Demanda
        fields = 'prioridade',
        verbose_name = 'Alterar Prioridade'

    def has_permission(self, user):
        return self.instance.solicitacao.ciclo.is_aberto() and self.instance.classificacao is not None and not self.instance.finalizada and self.instance.prioridade.numero > 1

    def get_prioridade_queryset(self, queryset):
        numero = self.instantiator.demanda_set.filter(classificacao=self.instance.classificacao).order_by('prioridade__numero').values_list('prioridade__numero', flat=True).last() or 0
        return queryset.filter(numero__lte=numero).exclude(numero=self.instance.prioridade.numero)

    def submit(self):
        prioridade = Demanda.objects.get(pk=self.instance.pk).prioridade
        demanda = self.instance.solicitacao.demanda_set.get(
            classificacao=self.instance.classificacao, prioridade=self.instance.prioridade
        )
        self.instance.save()
        demanda.prioridade = prioridade
        demanda.save()
        self.message('Ação realizada com sucesso')
        self.redirect()

    def has_permission(self, user):
        return not self.instance.finalizada and user.roles.contains('Gestor')


class AdicionarDemanda(actions.Action):
    class Meta:
        icon = 'plus'
        model = Demanda
        fields = 'classificacao', 'prioridade', 'descricao', 'valor_total', 'valor', 'unidades_beneficiadas'
        verbose_name = 'Adicionar Demanda'
        related_field = 'solicitacao'
        has_permission = 'Gestor',
        fieldsets = {
            'Dados Gerais': (('classificacao', 'prioridade'), 'descricao', ('valor_total', 'valor'), 'unidades_beneficiadas')
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        disponivel = self.instantiator.ciclo.teto - self.instantiator.demanda_set.exclude(pk=self.instance.pk).exclude(classificacao__contabilizar=False).sum('valor')
        self.fields['valor'].help_text = 'Valor Disponível R$: {}'.format(format_value(disponivel))

    def has_permission(self, user):
        return self.instantiator.ciclo.is_aberto() and not self.instantiator.is_finalizada()

    def clean_valor_total(self):
        valor_total = self.cleaned_data['valor_total']
        if Decimal(valor_total) < 176000:
            raise actions.ValidationError('O valor deve ser maior que R$ 176.000,00')
        return valor_total

    def clean_valor(self):
        valor = Decimal(self.cleaned_data['valor'])
        total = self.instantiator.demanda_set.exclude(pk=self.instance.pk).exclude(classificacao__contabilizar=False).sum('valor')
        if self.cleaned_data.get('classificacao', self.instance.classificacao).contabilizar and total + valor > self.instantiator.ciclo.teto:
            raise actions.ValidationError('O valor ultrapassa o limite orçamentário')
        if valor < 176000:
            raise actions.ValidationError('O valor deve ser maior que R$ 176.000,00')
        return valor

    def get_prioridade_queryset(self, queryset):
        limite = self.instantiator.ciclo.get_limites_demandas().get(classificacao=self.data['classificacao'])
        numero = self.instantiator.demanda_set.filter(classificacao=self.data['classificacao']).order_by('prioridade__numero').values_list('prioridade__numero', flat=True).last() or 0
        return queryset.filter(
            numero__gt=numero, numero__lte=min(numero+1, limite.quantidade)
        )

    def get_unidades_beneficiadas_queryset(self, queryset):
        return queryset.role_lookups('Gestor', instituicao='instituicao').apply_role_lookups(self.request.user)

    def get_classificacao_queryset(self, queryset):
        ids = []
        for limite in self.instantiator.ciclo.get_limites_demandas():
            if limite.quantidade > self.instantiator.demanda_set.filter(classificacao=limite.classificacao).count():
                ids.append(limite.classificacao.id)
        return queryset.filter(pk__in=ids)

    def submit(self):
        super().submit()


class AlterarDemanda(AdicionarDemanda):
    class Meta:
        model = Demanda
        fields = 'descricao', 'valor_total', 'valor', 'unidades_beneficiadas'
        verbose_name = 'Alterar Dados Gerais'
        fieldsets = {
            'Dados Gerais': ('descricao', ('valor_total', 'valor'), 'unidades_beneficiadas')
        }

    def has_permission(self, user):
        return self.instance.solicitacao.ciclo.is_aberto() and not self.instance.finalizada


class Reabrir(actions.Action):
    class Meta:
        verbose_name = 'Reabrir para Edição'
        style = 'warning'

    def has_permission(self, user):
        return self.instance.finalizada and (user.roles.contains('Administrador') or user.is_superuser)

    def submit(self):
        self.instance.finalizada = False
        self.instance.save()
        QuestionarioFinal.objects.filter(
            solicitacao=self.instance.solicitacao
        ).update(finalizado=False)
        super().submit()


class DetalharDemanda(actions.Action):

    class Meta:
        model = Demanda
        verbose_name = 'Detalhar Demanda'
        fields = []

    def has_permission(self, user):
        return not self.instance.finalizada and self.instance.solicitacao.ciclo.is_aberto() and user.roles.filter(name='Gestor').exists()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for pergunta_questionario in self.instance.get_questionario().respostaquestionario_set.all().order_by('pergunta__ordem'):
            tipo_resposta = pergunta_questionario.pergunta.tipo_resposta
            key = '{}'.format(pergunta_questionario.pk)
            self.initial[key] = pergunta_questionario.resposta
            if tipo_resposta == Pergunta.TEXTO_CURTO:
                self.fields[key] = actions.CharField(
                    label=str(pergunta_questionario.pergunta),
                    required=False
                )
            elif tipo_resposta == Pergunta.TEXTO_LONGO:
                self.fields[key] = actions.CharField(
                    label=str(pergunta_questionario.pergunta), widget=actions.Textarea(),
                    required=False
                )
            elif tipo_resposta == Pergunta.NUMERO_DECIMAL:
                self.fields[key] = actions.DecimalField(
                    label=str(pergunta_questionario.pergunta),
                    required=False, localize=True
                )
            elif tipo_resposta == Pergunta.NUMERO_INTEIRO:
                self.fields[key] = actions.IntegerField(
                    label=str(pergunta_questionario.pergunta),
                    required=False
                )
            elif tipo_resposta == Pergunta.DATA:
                self.fields[key] = actions.DateField(
                    label=str(pergunta_questionario.pergunta),
                    required=False
                )
            elif tipo_resposta == Pergunta.BOOLEANO:
                self.fields[key] = actions.ChoiceField(
                    label=str(pergunta_questionario.pergunta),
                    required=False,
                    choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']]
                )
            elif tipo_resposta == Pergunta.ARQUIVO:
                self.fields[key] = actions.FileField(
                    label=str(pergunta_questionario.pergunta),
                    required=False,
                )
            elif tipo_resposta == Pergunta.OPCOES:
                self.fields[key] = actions.ChoiceField(
                    label=str(pergunta_questionario.pergunta),
                    required=False,
                    choices=[['', '']] + [[str(x), str(x)] for x in pergunta_questionario.pergunta.opcoes.all()]
                )
            if pergunta_questionario.pergunta.obrigatoria:
                self.fields[key].label = '{} (Obrigatória)'.format(self.fields[key].label)

    def get_fieldsets(self):
        return {
            'Perguntas': list(self.fields.keys())
        }

    def submit(self):
        for pergunta_questionario in self.instance.get_questionario().respostaquestionario_set.all():
            key = '{}'.format(pergunta_questionario.pk)
            if pergunta_questionario.pergunta.tipo_resposta == Pergunta.ARQUIVO:
                arquivo = self.cleaned_data[key]
                if arquivo:
                    nome_aquivo = '{}.{}'.format(pergunta_questionario.pk, arquivo.name.split('.')[-1])
                    diretorio = os.path.join(settings.MEDIA_ROOT, 'arquivos')
                    os.makedirs(diretorio, exist_ok=True)
                    caminho = os.path.join(settings.MEDIA_ROOT, 'arquivos', nome_aquivo)
                    with open(caminho, 'wb+') as file:
                        file.write(arquivo.read())
                    resposta = os.path.join(settings.MEDIA_URL, 'arquivos', nome_aquivo)
                else:
                    resposta = None
            else:
                resposta = format_value(self.cleaned_data[key]) if self.cleaned_data[key] else None
            pergunta_questionario.resposta = resposta
            pergunta_questionario.save()
        if self.instance.get_progresso_questionario() == 100:
            self.instance.finalizada = True
            self.instance.save()
        self.message('Ação realizada com sucesso.')
        self.redirect()


class AlterarSenha(actions.Action):
    password = actions.CharField(label='Senha', widget=actions.PasswordInput())

    class Meta:
        verbose_name = 'Alterar Senha'

    def proces(self):
        self.instantiator.user.set_password(self.cleaned_data['password'])
        self.instantiator.user.save()


class VisualizarQuestionario(actions.Action):

    class Meta:
        verbose_name = 'Visualizar Questionário'

    def view(self):
        return self.instance.value_set('get_respostas_questionario')

    def has_permission(self, user):
        return self.instance.finalizada


class ConcluirSolicitacao(actions.Action):

    rco_pendente = actions.ChoiceField(
        label='A instituição possui RCO pendente de entrega para a SETEC?',
        choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']],
    )
    detalhe_rco_pendente = actions.CharField(
        label='Número do(s) TED(s) e o resumo da situação caso possua RCO pendente de entregue para a SETEC',
        required=False, widget=actions.Textarea()
    )
    prioridade_1 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 1', help_text='Dentre as demandas informadas, elenque a 1ª mais prioritária para este exercício.')
    prioridade_2 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 2', help_text='Dentre as demandas informadas, elenque a 2ª mais prioritária para este exercício.')
    prioridade_3 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 3', help_text='Dentre as demandas informadas, elenque a 3ª mais prioritária para este exercício.')
    prioridade_4 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 4', help_text='Dentre as demandas informadas, elenque a 4ª mais prioritária para este exercício.')
    prioridade_5 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 5', help_text='Dentre as demandas informadas, elenque a 5ª mais prioritária para este exercício.')

    class Meta:
        icon = 'check2-all'
        verbose_name = 'Concluir Solicitação'
        style = 'success'
        fieldsets = {
            'Demandas Prioritárias do Exercício': ('prioridade_1', 'prioridade_2', 'prioridade_3', 'prioridade_4', 'prioridade_5'),
            'Relatório de Cumprimento do Objeto (RCO)': ('rco_pendente', 'detalhe_rco_pendente'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial = {}
        questionario_final = QuestionarioFinal.objects.filter(solicitacao=self.instantiator).first()
        if questionario_final:
            self.initial.update(
                rco_pendente=questionario_final.rco_pendente,
                detalhe_rco_pendente=questionario_final.detalhe_rco_pendente,
                devolucao_ted=questionario_final.devolucao_ted,
                detalhe_devolucao_ted=questionario_final.detalhe_devolucao_ted,
                prioridade_1=questionario_final.prioridade_1_id,
                prioridade_2=questionario_final.prioridade_2_id,
                prioridade_3=questionario_final.prioridade_3_id,
                prioridade_4=questionario_final.prioridade_4_id,
                prioridade_5=questionario_final.prioridade_5_id,
            )

    def get_prioridade_queryset(self, queryset, n):
        ids = []
        for i in range(1, 6):
            id = self.data.get('prioridade_{}'.format(i))
            if id and i != n:
                ids.append(id)
        return self.instantiator.demanda_set.exclude(id__in=ids)

    def get_prioridade_1_queryset(self, queryset):
        return self.get_prioridade_queryset(queryset, 1)

    def get_prioridade_2_queryset(self, queryset):
        return self.get_prioridade_queryset(queryset, 2)

    def get_prioridade_3_queryset(self, queryset):
        return self.get_prioridade_queryset(queryset, 3)

    def get_prioridade_4_queryset(self, queryset):
        return self.get_prioridade_queryset(queryset, 4)

    def get_prioridade_5_queryset(self, queryset):
        return self.get_prioridade_queryset(queryset, 5)

    def has_permission(self, user):
        if user.roles.contains('Gestor') and self.instantiator.demanda_set.count() >=3 and not self.instantiator.is_finalizada():
            if not Demanda.objects.filter(solicitacao=self.instantiator, finalizada=False).exists():
                return not QuestionarioFinal.objects.filter(solicitacao=self.instantiator, finalizado=True).exists()
        return False

    def submit(self):
        questionario_final = QuestionarioFinal.objects.filter(solicitacao=self.instantiator).first() or QuestionarioFinal(solicitacao=self.instantiator)
        questionario_final.rco_pendente = self.cleaned_data['rco_pendente']
        questionario_final.detalhe_rco_pendente = self.cleaned_data['detalhe_rco_pendente']
        questionario_final.devolucao_ted = self.cleaned_data['devolucao_ted']
        questionario_final.detalhe_devolucao_ted = self.cleaned_data['detalhe_devolucao_ted']
        questionario_final.prioridade_1 = self.cleaned_data['prioridade_1']
        questionario_final.prioridade_2 = self.cleaned_data['prioridade_2']
        questionario_final.prioridade_3 = self.cleaned_data['prioridade_3']
        questionario_final.finalizado = True
        questionario_final.save()
        self.message('Solicitação concluída com sucesso.')
        self.redirect()


class CadastrarDuvida(actions.Action):
    class Meta:
        model = Duvida
        verbose_name = 'Tirar Dúvida'
        fields = 'pergunta',

    def save(self, *args, **kwargs):
        gestor = Gestor.objects.filter(email=self.request.user.username).first()
        self.instance.data_pergunta = datetime.now()
        self.instance.instituicao = gestor.instituicao
        return super().save(*args, **kwargs)

    def has_permission(self, user):
        return user.roles.contains('Gestor')


class ResponderDuvida(actions.Action):
    class Meta:
        model = Duvida
        verbose_name = 'Responder Dúvida'
        fields = 'resposta',

    def has_permission(self, user):
        if user.roles.filter(name='Administrador').exists():
            return True
        return False

    def save(self, *args, **kwargs):
        self.instance.data_resposta = datetime.now()
        return super().save(*args, **kwargs)


class ExportarResultado(actions.Action):

    instituicao = actions.ModelChoiceField(Instituicao.objects, label='Instituição', required=False)
    categoria = actions.ModelChoiceField(Categoria.objects, label='Categoria', required=False)
    prioridade = actions.ModelChoiceField(Prioridade.objects, label='Prioridade', required=False)

    class Meta:
        verbose_name = 'Exportar Resultado'
        icon = 'bi-file-exce'

    def submit(self):
        dados = list()
        demandas = list([['DEMANDA', 'CATEGORIA', 'INSTITUIÇÃO', 'UNIDADES BENEFICIADAS', 'PRIORIDADE', 'VALOR TOTAL', 'VALOR EMPENHO']])
        questionario = list([['DEMANDA', 'CATEGORIA', 'INSTITUIÇÃO', 'PRIORIDADE', 'VALOR TOTAL', 'VALOR EMPENHO', 'PERGUNTA', 'RESPOSTA']])
        fechamento = list([['INSTITUIÇÃO', 'PERGUNTA', 'RESPOSTA']])
        dados.append(('Demandas', demandas))
        dados.append(('Questionário', questionario))
        dados.append(('Fechamento', fechamento))
        instituicao = self.cleaned_data['instituicao']
        categoria = self.cleaned_data['categoria']
        prioridade = self.cleaned_data['prioridade']
        qs = self.instance.get_demandas()
        qs = qs.filter(solicitacao__instituicao=instituicao) if instituicao else qs
        qs = qs.filter(classificacao=categoria) if categoria else qs
        qs = qs.filter(prioridade=prioridade) if prioridade else qs
        demanda = None
        for demanda in qs.filter(valor__isnull=False).exclude(valor=0):
            l1 = [demanda.descricao, demanda.classificacao.nome, demanda.solicitacao.instituicao.sigla, ', '.join(demanda.unidades_beneficiadas.values_list('nome', flat=True)), demanda.prioridade.numero, demanda.valor_total, demanda.valor]
            demandas.append(l1)
            for resposta_questionario in demanda.get_respostas_questionario():
                l2 = list(l1)
                l2.append(str(resposta_questionario.pergunta))
                if resposta_questionario.resposta is not None:
                    l2.append(resposta_questionario.resposta)
                questionario.append(l2)

        if demanda is not None:
            instituicoes = demanda.solicitacao.ciclo.instituicoes.all()
            if instituicao:
                instituicoes = instituicoes.filter(pk=instituicao.pk)
            for instituicao1 in instituicoes:
                questionario_final = demanda.solicitacao.questionariofinal_set.first()
                if questionario_final:
                    fechamento.append([instituicao1.sigla, 'Prioridade 01', questionario_final.prioridade_1.descricao if questionario_final.prioridade_1 else ''])
                    fechamento.append([instituicao1.sigla, 'Prioridade 02', questionario_final.prioridade_2.descricao if questionario_final.prioridade_2 else ''])
                    fechamento.append([instituicao1.sigla, 'Prioridade 03', questionario_final.prioridade_3.descricao if questionario_final.prioridade_3 else ''])
                    fechamento.append([instituicao1.sigla, 'Prioridade 04', questionario_final.prioridade_4.descricao if questionario_final.prioridade_4 else ''])
                    fechamento.append([instituicao1.sigla, 'Prioridade 05', questionario_final.prioridade_5.descricao if questionario_final.prioridade_5 else ''])
                    fechamento.append([instituicao1.sigla, 'A instituição possui RCO pendente de entrega para a SETEC?', questionario_final.rco_pendente or ''])
                    fechamento.append([instituicao1.sigla, 'Número do(s) TED(s) e o resumo da situação caso possua RCO pendente de entregue para a SETEC', questionario_final.detalhe_rco_pendente or ''])
                    fechamento.append([instituicao1.sigla, 'A instituição devolveu algum valor de TED em 2021?', questionario_final.devolucao_ted or ''])
                    fechamento.append([instituicao1.sigla, 'Número do(s) TED(s) e o resumo da situação caso tenha devolvido algum valor de TED em 2021', questionario_final.detalhe_devolucao_ted or ''])
        return XlsResponse(dados)

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class ExportarResultadoPorCategoria(actions.Action):

    instituicao = actions.ModelChoiceField(Instituicao.objects, label='Instituição', required=False)
    categoria = actions.ModelChoiceField(Categoria.objects, label='Categoria', required=False)
    prioridade = actions.ModelChoiceField(Prioridade.objects, label='Prioridade', required=False)

    class Meta:
        verbose_name = 'Exportar Resultado por Categoria'
        icon = 'bi-file-exce'

    def submit(self):
        dados = list()
        demandas = ['DEMANDA', 'CATEGORIA', 'INSTITUIÇÃO', 'UNIDADES BENEFICIADAS', 'PRIORIDADE', 'VALOR TOTAL', 'VALOR EMPENHO']
        instituicao = self.cleaned_data['instituicao']
        categoria = self.cleaned_data['categoria']
        prioridade = self.cleaned_data['prioridade']
        qs = self.instance.get_demandas()
        qs = qs.filter(solicitacao__instituicao=instituicao) if instituicao else qs
        qs = qs.filter(classificacao=categoria) if categoria else qs
        qs = qs.filter(prioridade=prioridade) if prioridade else qs
        ids = qs.order_by('classificacao').values_list('classificacao', flat=True).distinct()
        for i, classificacao in enumerate(Categoria.objects.filter(id__in=ids)):
            linhas = list()
            cabecalho = list(demandas)
            perguntas = classificacao.pergunta_set.order_by('ordem').all()
            for pergunta in perguntas:
                cabecalho.append(pergunta.texto.upper())
            linhas.append(cabecalho)
            for demanda in qs.filter(valor__isnull=False).exclude(valor=0).filter(classificacao=classificacao):
                linha = [demanda.descricao, demanda.classificacao.nome, demanda.solicitacao.instituicao.sigla, ', '.join(demanda.unidades_beneficiadas.values_list('nome', flat=True)), demanda.prioridade.numero, demanda.valor_total, demanda.valor]
                for pergunta in perguntas:
                    resposta_questionario = demanda.get_respostas_questionario().filter(pergunta=pergunta).first()
                    if resposta_questionario:
                        if resposta_questionario.resposta is None:
                            linha.append('')
                        else:
                            linha.append(resposta_questionario.resposta)
                linhas.append(linha)
            dados.append((str(i+1), linhas))
        return XlsResponse(dados)

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class EnviarSenhas(actions.Action):
    reenviar = actions.BooleanField(label='Re-enviar mesmo em caso de já ter sido notificado', required=False)

    class Meta:
        verbose_name = 'Enviar Senhas'
        style = 'primary'

    def submit(self):
        qs = self.instances if self.instances else Gestor.objects.all()
        if self.cleaned_data['reenviar']:
            qs.update(notificado=False)
        for gestor in qs:
            print(gestor.email)
            enviar_senha(gestor)
            gestor.notificado = True
            gestor.save()
        self.message('E-mails enviados com sucesso.')
        self.redirect()
    def has_permission(self, user):
        return user.roles.contains('Administrador')