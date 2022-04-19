# -*- coding: utf-8 -*-
import os
from datetime import datetime
from django.conf import settings
from sloth import actions
from sloth.utils.formatter import format_value
from sloth.utils.http import XlsResponse

from .models import Campus, Demanda, Pergunta, Gestor, QuestionarioFinal, Duvida, Instituicao, Categoria, Prioridade


class AdicionarGestor(actions.Action):
    class Meta:
        model = Gestor
        fields = 'nome', 'email'
        verbose_name = 'Adicionar Gestor'
        parent = 'instituicao'
        has_permission = 'Administrador',


class AdicionarPergunta(actions.Action):
    class Meta:
        model = Pergunta
        verbose_name = 'Adicionar Pergunta'
        parent = 'categoria'
        fieldsets = {
            'Dados Gerais': ('ordem', 'texto', 'tipo_resposta', 'obrigatoria'),
            'Opções de Resposta': ('opcoes',)
        }
        has_permission = 'Administrador',


class AdicionarCampus(actions.Action):
    class Meta:
        model = Campus
        fields = 'nome',
        verbose_name = 'Adicionar Campus'
        parent = 'instituicao'
        has_permission = 'Administrador',


class AlterarPrioridade(actions.Action):
    class Meta:
        model = Demanda
        fields = 'prioridade',
        verbose_name = 'Alterar Prioridade'
        has_permission = 'Gestor',

    def has_permission(self, user):
        return self.instance.ciclo.is_aberto() and self.instance.classificacao is not None and not self.instance.finalizada and self.instance.prioridade.numero > 1

    def get_prioridade_queryset(self, queryset):
        return queryset.filter(
            numero__lte=self.instance.ciclo.get_limites_demandas().get(classificacao=self.instance.classificacao).quantidade
        ).exclude(numero=self.instance.prioridade.numero)

    def save(self, *args, **kwargs):
        prioridade = Demanda.objects.get(pk=self.instance.pk).prioridade
        demanda = self.instance.ciclo.demanda_set.get(
            instituicao=self.instance.instituicao, prioridade=self.instance.prioridade, classificacao=self.instance.classificacao
        )
        demanda.prioridade = prioridade
        demanda.save()
        super().save(*args, **kwargs)


class NaoInformarDemanda(actions.Action):
    class Meta:
        model = Demanda
        fields = ()
        verbose_name = 'Não Informar'
        style = 'danger'
        has_permission = 'Gestor',

    def save(self, *args, **kwargs):
        self.instance.valor = 0
        self.instance.valor_total = 0
        self.instance.descricao = 'Não Informado'
        self.instance.finalizada = True
        super().save(*args, **kwargs)

    def has_permission(self, user):
        return self.instance.ciclo.is_aberto() and not self.instance.finalizada


class PreencherDemanda(actions.Action):
    class Meta:
        model = Demanda
        fields = 'classificacao', 'prioridade', 'descricao', 'valor_total', 'valor', 'unidades_beneficiadas'
        verbose_name = 'Preencher Dados Gerais'
        has_permission = 'Gestor',

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        disponivel = self.instance.ciclo.teto - self.instance.ciclo.demanda_set.filter(instituicao=self.instance.instituicao).exclude(pk=self.instance.pk).exclude(classificacao__contabilizar=False).sum('valor')
        self.fields['classificacao'].widget.attrs.update(readonly='readonly')
        self.fields['prioridade'].widget.attrs.update(readonly='readonly')
        self.fields['valor'].help_text = 'Valor Disponível R$: {}'.format(format_value(disponivel))

    def has_permission(self, user):
        return self.instance.ciclo.is_aberto() and not self.instance.finalizada

    def clean_valor_total(self):
        valor_total = self.cleaned_data['valor_total']
        if valor_total < 176000:
            raise actions.ValidationError('O valor deve ser maior que R$ 176.000,00')
        return valor_total

    def clean_valor(self):
        valor = self.cleaned_data['valor']
        total = self.instance.ciclo.demanda_set.filter(instituicao=self.instance.instituicao).exclude(pk=self.instance.pk).exclude(classificacao__contabilizar=False).sum('valor')
        if self.instance.classificacao.contabilizar and total + valor > self.instance.ciclo.teto:
            raise actions.ValidationError(
                'Esse valor faz com que o limite de investimento para a instituição seja ultrapassado.')
        if valor < 176000:
            raise actions.ValidationError('O valor deve ser maior que R$ 176.000,00')
        return valor

    def get_unidades_beneficiadas_queryset(self, queryset):
        return queryset.role_lookups('Gestor', instituicao='instituicao').apply_role_lookups(self.request.user)


class AlterarPreenchimento(PreencherDemanda):
    class Meta:
        model = Demanda
        fields = 'classificacao', 'prioridade', 'descricao', 'valor_total', 'valor', 'unidades_beneficiadas'
        verbose_name = 'Alterar Dados Gerais'
        has_permission = 'Gestor',


class Reabir(actions.Action):
    class Meta:
        model = Demanda
        fields = ()
        verbose_name = 'Reabir para Edição'
        has_permission = 'Administrador',

    def save(self, *args, **kwargs):
        self.instance.finalizada = False
        QuestionarioFinal.objects.filter(
            ciclo=self.instance.ciclo, instituicao=self.instance.instituicao
        ).update(finalizado=False)
        super().save(*args, **kwargs)


class DetalharDemanda(actions.Action):

    class Meta:
        model = Demanda
        verbose_name = 'Detalhar Demanda'
        fields = []

    def has_permission(self, user):
        return self.instance.ciclo.is_aberto() and user.roles.filter(name='Gestor').exists() and self.instance.get_questionario() is not None

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
        reload = not Demanda.objects.filter(
            ciclo=self.instance.ciclo, instituicao=self.instance.instituicao, finalizada=False
        ).exists()
        self.redirect('.' if reload else '..')


class AlterarDetalhamentoDemanda(DetalharDemanda):

    class Meta:
        model = Demanda
        verbose_name = 'Alterar Detalhamento'
        fields = []

    def has_permission(self, user):
        if self.instance.valor and user.roles.filter(name='Gestor').exists():
            questionario_final = QuestionarioFinal.objects.filter(
                ciclo=self.instance.ciclo, instituicao=self.instance.instituicao
            )
            return self.instance.ciclo.is_aberto() and not questionario_final.filter(finalizado=True).exists()
        return False


class AlterarSenha(actions.Action):
    password = actions.CharField(label='Senha', widget=actions.PasswordInput())

    class Meta:
        verbose_name = 'Alterar Senha'

    def proces(self):
        self.instantiator.user.set_password(self.cleaned_data['password'])
        self.instantiator.user.save()


class ConcluirSolicitacao(actions.Action):

    rco_pendente = actions.ChoiceField(
        label='A instituição possui RCO pendente de entrega para a SETEC?',
        choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']],
    )
    detalhe_rco_pendente = actions.CharField(
        label='Número do(s) TED(s) e o resumo da situação caso possua RCO pendente de entregue para a SETEC',
        required=False, widget=actions.Textarea()
    )
    devolucao_ted = actions.ChoiceField(
        label='A instituição devolveu algum valor de TED em 2021?',
        choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']],
    )
    detalhe_devolucao_ted = actions.CharField(
        label='Número do(s) TED(s) e o resumo da situação caso tenha devolvido algum valor de TED em 2021',
        required=False, widget=actions.Textarea()
    )
    prioridade_1 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 1', help_text='Dentre as demandas informadas, elenque a 1ª mais prioritária para este exercício.')
    prioridade_2 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 2', help_text='Dentre as demandas informadas, elenque a 2ª mais prioritária para este exercício.')
    prioridade_3 = actions.ModelChoiceField(Demanda.objects, label='Prioridade 3', help_text='Dentre as demandas informadas, elenque a 3ª mais prioritária para este exercício.')

    class Meta:
        verbose_name = 'Concluir Solicitação'
        has_permission = 'Gestor',
        style = 'success'
        fieldsets = {
            'Demandas Prioritárias do Exercício': ('prioridade_1', 'prioridade_2', 'prioridade_3'),
            'Relatório de Cumprimento do Objeto (RCO)': ('rco_pendente', 'detalhe_rco_pendente'),
            'Transferência Eletrônica Descentralizada (TED)': ('devolucao_ted', 'detalhe_devolucao_ted'),
        }

    def __init__(self, *args, **kwargs):
        initial = {}
        gestor = Gestor.objects.filter(email=kwargs['request'].user.username).first()
        ciclo = kwargs['instantiator']
        instituicao = gestor.instituicao
        questionario_final = QuestionarioFinal.objects.filter(
            ciclo=ciclo, instituicao=instituicao
        ).first()
        if questionario_final:
            initial.update(
                rco_pendente=questionario_final.rco_pendente,
                detalhe_rco_pendente=questionario_final.detalhe_rco_pendente,
                devolucao_ted=questionario_final.devolucao_ted,
                detalhe_devolucao_ted=questionario_final.detalhe_devolucao_ted,
                prioridade_1=questionario_final.prioridade_1_id,
                prioridade_2=questionario_final.prioridade_2_id,
                prioridade_3=questionario_final.prioridade_3_id
            )
        kwargs.update(initial=initial)
        super().__init__(*args, **kwargs)
        self.fields['prioridade_1'].queryset = ciclo.demanda_set.filter(instituicao=instituicao, descricao__isnull=False)
        self.fields['prioridade_2'].queryset = ciclo.demanda_set.filter(instituicao=instituicao, descricao__isnull=False)
        self.fields['prioridade_3'].queryset = ciclo.demanda_set.filter(instituicao=instituicao, descricao__isnull=False)

    def has_permission(self, user):
        if user.roles.filter(name='Gestor').exists():
            gestor = Gestor.objects.filter(email=user.username).first()
            ciclo = self.instantiator
            instituicao = gestor.instituicao
            demandas_finalizadas = not Demanda.objects.filter(ciclo=ciclo, instituicao=instituicao, finalizada=False).exists()
            questionario_final = QuestionarioFinal.objects.filter(ciclo=ciclo, instituicao=instituicao, finalizado=True).first()
            return demandas_finalizadas and not questionario_final
        return False

    def submit(self):
        gestor = Gestor.objects.filter(email=self.request.user.username).first()
        ciclo = self.instantiator
        instituicao = gestor.instituicao
        questionario_final = QuestionarioFinal.objects.filter(
            ciclo=ciclo, instituicao=instituicao
        ).first() or QuestionarioFinal(ciclo=ciclo, instituicao=instituicao)
        questionario_final.rco_pendente = self.cleaned_data['rco_pendente']
        questionario_final.detalhe_rco_pendente = self.cleaned_data['detalhe_rco_pendente']
        questionario_final.devolucao_ted = self.cleaned_data['devolucao_ted']
        questionario_final.detalhe_devolucao_ted = self.cleaned_data['detalhe_devolucao_ted']
        questionario_final.prioridade_1 = self.cleaned_data['prioridade_1']
        questionario_final.prioridade_2 = self.cleaned_data['prioridade_2']
        questionario_final.prioridade_3 = self.cleaned_data['prioridade_3']
        questionario_final.finalizado = True
        questionario_final.save()
        self.redirect(message='Solicitação concluída com sucesso.')


class AddForm(actions.Action):
    class Meta:
        model = Duvida
        verbose_name = 'Tirar Dúvida'
        fields = 'pergunta',
        has_permission = 'Gestor',

    def save(self, *args, **kwargs):
        gestor = Gestor.objects.filter(email=self.request.user.username).first()
        self.instance.data_pergunta = datetime.now()
        self.instance.instituicao = gestor.instituicao
        return super().save(*args, **kwargs)


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


class RestaurarDemanda(actions.Action):
    class Meta:
        model = Demanda
        verbose_name = 'Restaurar'
        fields = ()
        style = 'danger'

    def has_permission(self, user):
        if user.roles.filter(name='Administrador').exists() and self.instance.descricao:
            return True
        return False

    def save(self, *args, **kwargs):
        self.instance.descricao = ''
        self.instance.valor = None
        self.instance.valor_total = None
        return super().save(*args, **kwargs)


class ExportarResultado(actions.Action):

    instituicao = actions.ModelChoiceField(Instituicao.objects, label='Instituição', required=False)
    categoria = actions.ModelChoiceField(Categoria.objects, label='Categoria', required=False)
    prioridade = actions.ModelChoiceField(Prioridade.objects, label='Prioridade', required=False)

    class Meta:
        verbose_name = 'Exportar Resultado'
        has_permission = 'Administrador',
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
        qs = self.instantiator.demanda_set.all()
        qs = qs.filter(instituicao=instituicao) if instituicao else qs
        qs = qs.filter(classificacao=categoria) if categoria else qs
        qs = qs.filter(prioridade=prioridade) if prioridade else qs
        demanda = None
        for demanda in qs.filter(valor__isnull=False).exclude(valor=0):
            l1 = [demanda.descricao, demanda.classificacao.nome, demanda.instituicao.sigla, ', '.join(demanda.unidades_beneficiadas.values_list('nome', flat=True)), demanda.prioridade.numero, demanda.valor_total, demanda.valor]
            demandas.append(l1)
            for resposta_questionario in demanda.get_respostas_questionario():
                l2 = list(l1)
                l2.append(str(resposta_questionario.pergunta))
                if resposta_questionario.resposta is not None:
                    l2.append(resposta_questionario.resposta)
                questionario.append(l2)

        if demanda is not None:
            instituicoes = demanda.ciclo.instituicoes.all()
            if instituicao:
                instituicoes = instituicoes.filter(pk=instituicao.pk)
            for instituicao1 in instituicoes:
                questionario_final = demanda.ciclo.get_questionario_final().filter(instituicao=instituicao1).first()
                if questionario_final:
                    fechamento.append([instituicao1.sigla, 'A instituição possui RCO pendente de entrega para a SETEC?', questionario_final.rco_pendente or ''])
                    fechamento.append([instituicao1.sigla, 'Número do(s) TED(s) e o resumo da situação caso possua RCO pendente de entregue para a SETEC', questionario_final.detalhe_rco_pendente or ''])
                    fechamento.append([instituicao1.sigla, 'A instituição devolveu algum valor de TED em 2021?', questionario_final.devolucao_ted or ''])
                    fechamento.append([instituicao1.sigla, 'Número do(s) TED(s) e o resumo da situação caso tenha devolvido algum valor de TED em 2021', questionario_final.detalhe_devolucao_ted or ''])
        self.http_response(XlsResponse(dados))


class ExportarResultadoPorCategoria(actions.Action):

    instituicao = actions.ModelChoiceField(Instituicao.objects, label='Instituição', required=False)
    categoria = actions.ModelChoiceField(Categoria.objects, label='Categoria', required=False)
    prioridade = actions.ModelChoiceField(Prioridade.objects, label='Prioridade', required=False)

    class Meta:
        verbose_name = 'Exportar Resultado por Categoria'
        has_permission = 'Administrador',
        icon = 'bi-file-exce'

    def submit(self):
        dados = list()
        demandas = ['DEMANDA', 'CATEGORIA', 'INSTITUIÇÃO', 'UNIDADES BENEFICIADAS', 'PRIORIDADE', 'VALOR TOTAL', 'VALOR EMPENHO']
        instituicao = self.cleaned_data['instituicao']
        categoria = self.cleaned_data['categoria']
        prioridade = self.cleaned_data['prioridade']
        qs = self.instantiator.demanda_set.all()
        qs = qs.filter(instituicao=instituicao) if instituicao else qs
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
                linha = [demanda.descricao, demanda.classificacao.nome, demanda.instituicao.sigla, ', '.join(demanda.unidades_beneficiadas.values_list('nome', flat=True)), demanda.prioridade.numero, demanda.valor_total, demanda.valor]
                for pergunta in perguntas:
                    resposta_questionario = demanda.get_respostas_questionario().filter(pergunta=pergunta).first()
                    if resposta_questionario:
                        if resposta_questionario.resposta is None:
                            linha.append('')
                        else:
                            linha.append(resposta_questionario.resposta)
                linhas.append(linha)
            dados.append((str(i+1), linhas))
        self.http_response(XlsResponse(dados))
