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
            'Dados Gerais': ('texto', 'tipo_resposta', 'obrigatoria'),
            'Opções de Resposta': ('opcoes',)
        }

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class EditarPergunta(actions.Action):
    class Meta:
        model = Pergunta
        verbose_name = 'Editar'
        fieldsets = {
            'Dados Gerais': ('texto', 'tipo_resposta', 'obrigatoria'),
            'Opções de Resposta': ('opcoes',)
        }

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class ReordenarPergunta(actions.Action):
    class Meta:
        style = 'warning'
        verbose_name = 'Mover para Cima'

    def submit(self):
        ordem = self.instance.ordem
        anterior = self.instance.categoria.pergunta_set.get(ordem=ordem-1)
        self.instance.ordem = anterior.ordem
        self.instance.save()
        anterior.ordem = ordem
        anterior.save()
        self.message()
        self.redirect()

    def has_permission(self, user):
        return self.instance.ordem > 1 and user.roles.contains('Administrador')


class AdicionarCampus(actions.Action):
    class Meta:
        model = Campus
        fields = 'nome',
        verbose_name = 'Adicionar Campus'
        related_field = 'instituicao'

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class EditarCampus(actions.Action):
    class Meta:
        model = Campus
        fields = 'nome',
        verbose_name = 'Editar'

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class EditarEmailGestor(actions.Action):
    class Meta:
        model = Gestor
        fields = 'email',
        verbose_name = 'Editar E-mail'

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class AlterarPrioridade(actions.Action):

    class Meta:
        style = 'warning'
        model = Demanda
        fields = 'prioridade',
        verbose_name = 'Elevar Prioridade'

    def has_permission(self, user):
        return self.instance.solicitacao.ciclo.is_aberto() and self.instance.classificacao is not None and not self.instance.finalizada and self.instance.prioridade.numero > 1

    def get_prioridade_queryset(self, queryset):
        numero = self.instantiator.demanda_set.filter(classificacao=self.instance.classificacao).order_by('prioridade__numero').values_list('prioridade__numero', flat=True).last() or 0
        return queryset.filter(numero__lt=numero).exclude(numero=self.instance.prioridade.numero)

    def submit(self):
        prioridade = Demanda.objects.get(pk=self.instance.pk).prioridade
        self.instance.solicitacao.demanda_set.filter(prioridade=self.instance.prioridade, classificacao=self.instance.classificacao).update(prioridade=prioridade)
        super().submit()

    def has_permission(self, user):
        return self.instance.id and self.instance.prioridade_id > 1 and not self.instance.finalizada and user.roles.contains('Gestor')


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
        quantidade = self.instantiator.demanda_set.filter(classificacao=self.data['classificacao']).count()
        return queryset.filter(numero=quantidade+1) if quantidade < limite.quantidade else queryset.none()

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
        return self.instance.id and self.instance.solicitacao.ciclo.is_aberto() and not self.instance.finalizada


class Reabrir(actions.Action):
    class Meta:
        verbose_name = 'Reabrir para Edição'
        style = 'warning'

    def has_permission(self, user):
        return self.instance.id and self.instance.finalizada and (user.roles.contains('Administrador') or user.is_superuser)

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
        return self.instance.id and not self.instance.solicitacao.is_finalizada() and self.instance.solicitacao.ciclo.is_aberto() and user.roles.filter(name='Gestor').exists()

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
    prioridade_2 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 2', help_text='Dentre as demandas informadas, elenque a 2ª mais prioritária para este exercício.', required=False)
    prioridade_3 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 3', help_text='Dentre as demandas informadas, elenque a 3ª mais prioritária para este exercício.', required=False)
    prioridade_4 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 4', help_text='Dentre as demandas informadas, elenque a 4ª mais prioritária para este exercício.', required=False)
    prioridade_5 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 5', help_text='Dentre as demandas informadas, elenque a 5ª mais prioritária para este exercício.', required=False)

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
        self.info('ATENÇÃO: Ao concluir a solicitação, não será mais possível adicionar novas demandas. Portanto, certifique-se que todas as demandas da sua instituição foram cadastradas.')
        questionario_final = QuestionarioFinal.objects.filter(solicitacao=self.instantiator).first()
        if questionario_final:
            self.initial.update(
                rco_pendente=questionario_final.rco_pendente,
                detalhe_rco_pendente=questionario_final.detalhe_rco_pendente,
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
        if user.roles.contains('Gestor') and self.instantiator.demanda_set.count() and not self.instantiator.demanda_set.filter(finalizada=False).exists() and not self.instantiator.is_finalizada():
            return not QuestionarioFinal.objects.filter(solicitacao=self.instantiator, finalizado=True).exists()
        return False

    def submit(self):
        questionario_final = QuestionarioFinal.objects.filter(solicitacao=self.instantiator).first() or QuestionarioFinal(solicitacao=self.instantiator)
        questionario_final.rco_pendente = self.cleaned_data['rco_pendente']
        questionario_final.detalhe_rco_pendente = self.cleaned_data['detalhe_rco_pendente']
        questionario_final.devolucao_ted = ''
        questionario_final.detalhe_devolucao_ted = None
        questionario_final.prioridade_1 = self.cleaned_data['prioridade_1']
        questionario_final.prioridade_2 = self.cleaned_data['prioridade_2']
        questionario_final.prioridade_3 = self.cleaned_data['prioridade_3']
        questionario_final.prioridade_4 = self.cleaned_data['prioridade_4']
        questionario_final.prioridade_5 = self.cleaned_data['prioridade_5']
        questionario_final.finalizado = True
        questionario_final.save()
        self.message('Solicitação concluída com sucesso.')
        self.redirect()


class CadastrarDuvida(actions.Action):
    class Meta:
        icon = 'question'
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

    def view(self):
        return self.instance.value_set('pergunta')

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
        demandas = list([['DEMANDA', 'CATEGORIA', 'INSTITUIÇÃO', 'UNIDADES BENEFICIADAS', 'PRIORIDADE', 'VALOR TOTAL', 'VALOR EMPENHO', 'ID']])
        questionario = list([['DEMANDA', 'CATEGORIA', 'INSTITUIÇÃO', 'PRIORIDADE', 'VALOR TOTAL', 'VALOR EMPENHO', 'PERGUNTA', 'RESPOSTA', 'ID']])
        fechamento = list([['INSTITUIÇÃO', 'PERGUNTA', 'RESPOSTA', 'ID']])
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
            l1 = [demanda.descricao, demanda.classificacao.nome, demanda.solicitacao.instituicao.sigla, ', '.join(demanda.unidades_beneficiadas.values_list('nome', flat=True)), demanda.prioridade.numero, demanda.valor_total, demanda.valor, demanda.id]
            demandas.append(l1)
            for resposta_questionario in demanda.get_respostas_questionario():
                l2 = list(l1)
                l2.append(str(resposta_questionario.pergunta))
                if resposta_questionario.resposta is not None:
                    l2.append(resposta_questionario.resposta)
                else:
                    l2.append('')
                l2.append(demanda.id)
                questionario.append(l2)

        if 1:
            instituicoes = self.instance.instituicoes.all()
            if instituicao:
                instituicoes = instituicoes.filter(pk=instituicao.pk)
            for instituicao1 in instituicoes:
                questionario_final = self.instance.solicitacao_set.get(instituicao=instituicao1).questionariofinal_set.first()
                if questionario_final:
                    fechamento.append([instituicao1.sigla, 'Prioridade 01', questionario_final.prioridade_1.descricao if questionario_final.prioridade_1 else '', questionario_final.prioridade_1_id or ''])
                    fechamento.append([instituicao1.sigla, 'Prioridade 02', questionario_final.prioridade_2.descricao if questionario_final.prioridade_2 else '', questionario_final.prioridade_2_id or ''])
                    fechamento.append([instituicao1.sigla, 'Prioridade 03', questionario_final.prioridade_3.descricao if questionario_final.prioridade_3 else '', questionario_final.prioridade_3_id or ''])
                    fechamento.append([instituicao1.sigla, 'Prioridade 04', questionario_final.prioridade_4.descricao if questionario_final.prioridade_4 else '', questionario_final.prioridade_4_id or ''])
                    fechamento.append([instituicao1.sigla, 'Prioridade 05', questionario_final.prioridade_5.descricao if questionario_final.prioridade_5 else '', questionario_final.prioridade_5_id or ''])
                    fechamento.append([instituicao1.sigla, 'A instituição possui RCO pendente de entrega para a SETEC?', questionario_final.rco_pendente or ''])
                    fechamento.append([instituicao1.sigla, 'Número do(s) TED(s) e o resumo da situação caso possua RCO pendente de entregue para a SETEC', questionario_final.detalhe_rco_pendente or ''])
                    fechamento.append([instituicao1.sigla, 'A instituição devolveu algum valor de TED em 2021?', questionario_final.devolucao_ted or ''])
                    fechamento.append([instituicao1.sigla, 'Número do(s) TED(s) e o resumo da situação caso tenha devolvido algum valor de TED em 2021', questionario_final.detalhe_devolucao_ted or ''])
        return XlsResponse(dados)

    def has_permission(self, user):
        return user.is_superuser or user.roles.contains('Administrador')


class ExportarResultadoPorCategoria(actions.Action):

    instituicao = actions.ModelChoiceField(Instituicao.objects, label='Instituição', required=False)
    categoria = actions.ModelChoiceField(Categoria.objects, label='Categoria', required=False)
    prioridade = actions.ModelChoiceField(Prioridade.objects, label='Prioridade', required=False)

    class Meta:
        verbose_name = 'Exportar Resultado por Categoria'
        icon = 'bi-file-exce'

    def submit(self):
        dados = list()
        rotulos = ['Obras', 'Equipamentos', 'Acessibilidade', 'PPCIP', 'Fotovoltaicas', 'Incidentes Climáticos', 'Saneamento Básico']
        demandas = ['DEMANDA', 'CATEGORIA', 'INSTITUIÇÃO', 'UNIDADES BENEFICIADAS', 'PRIORIDADE', 'VALOR TOTAL', 'VALOR EMPENHO', 'ID']
        instituicao = self.cleaned_data['instituicao']
        categoria = self.cleaned_data['categoria']
        prioridade = self.cleaned_data['prioridade']
        qs = self.instance.get_demandas()
        qs = qs.filter(solicitacao__instituicao=instituicao) if instituicao else qs
        qs = qs.filter(classificacao=categoria) if categoria else qs
        qs = qs.filter(prioridade=prioridade) if prioridade else qs
        dados.append(('Demandas', [demandas]))
        ids = qs.order_by('classificacao').values_list('classificacao', flat=True).distinct()
        for i, classificacao in enumerate(Categoria.objects.filter(id__in=ids)):
            linhas = list()
            cabecalho = list(demandas)
            perguntas = classificacao.pergunta_set.order_by('ordem').all()
            for pergunta in perguntas:
                cabecalho.append(pergunta.texto.upper())
            linhas.append(cabecalho)
            for demanda in qs.filter(valor__isnull=False).exclude(valor=0).filter(classificacao=classificacao):
                linha = [demanda.descricao, demanda.classificacao.nome, demanda.solicitacao.instituicao.sigla, ', '.join(demanda.unidades_beneficiadas.values_list('nome', flat=True)), demanda.prioridade.numero, demanda.valor_total, demanda.valor, demanda.id]
                dados[0][1].append(list(linha))
                for pergunta in perguntas:
                    resposta_questionario = demanda.get_respostas_questionario().filter(pergunta=pergunta).first()
                    if resposta_questionario:
                        if resposta_questionario.resposta is None:
                            linha.append('')
                        else:
                            linha.append(resposta_questionario.resposta)
                linhas.append(linha)
            dados.append((rotulos[i], linhas))
        fechamento = list([['INSTITUIÇÃO', 'PERGUNTA', 'RESPOSTA', 'ID']])
        dados.append(('Fechamento', fechamento))
        instituicoes = self.instance.instituicoes.all()
        if instituicao:
            instituicoes = instituicoes.filter(pk=instituicao.pk)
        for inst in instituicoes:
            quest = self.instance.solicitacao_set.get(instituicao=inst).questionariofinal_set.first()
            if quest:
                fechamento.append([inst.sigla, 'Prioridade 01', quest.prioridade_1.descricao if quest.prioridade_1 else '', quest.prioridade_1_id or ''])
                fechamento.append([inst.sigla, 'Prioridade 02', quest.prioridade_2.descricao if quest.prioridade_2 else '', quest.prioridade_2_id or ''])
                fechamento.append([inst.sigla, 'Prioridade 03', quest.prioridade_3.descricao if quest.prioridade_3 else '', quest.prioridade_3_id or ''])
                fechamento.append([inst.sigla, 'Prioridade 04', quest.prioridade_4.descricao if quest.prioridade_4 else '', quest.prioridade_4_id or ''])
                fechamento.append([inst.sigla, 'Prioridade 05', quest.prioridade_5.descricao if quest.prioridade_5 else '', quest.prioridade_5_id or ''])
                fechamento.append([inst.sigla, 'A instituição possui RCO pendente de entrega para a SETEC?', quest.rco_pendente or ''])
                fechamento.append([inst.sigla, 'Número do(s) TED(s) e o resumo da situação caso possua RCO pendente de entregue para a SETEC', quest.detalhe_rco_pendente or ''])
                fechamento.append([inst.sigla, 'A instituição devolveu algum valor de TED em 2021?', quest.devolucao_ted or ''])
                fechamento.append([inst.sigla, 'Número do(s) TED(s) e o resumo da situação caso tenha devolvido algum valor de TED em 2021', quest.detalhe_devolucao_ted or ''])
        return XlsResponse(dados)

    def has_permission(self, user):
        return user.is_superuser or user.roles.contains('Administrador')


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


class DescartarDemanda(actions.Action):

    class Meta:
        verbose_name = 'Descartar Demanda'
        style = 'danger'

    def submit(self):
        self.instance.delete()
        self.message()
        self.redirect()

    def has_permission(self, user):
        return user.roles.contains('Gestor') and not self.instance.finalizada
