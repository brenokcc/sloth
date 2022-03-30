# -*- coding: utf-8 -*-
import os
from datetime import datetime

from django.conf import settings
from sloth import forms
from sloth.utils.formatter import format_value
from sloth.utils.http import XlsResponse

from .models import Campus, Demanda, Pergunta, Gestor, QuestionarioFinal, Duvida, Instituicao, Categoria, Prioridade


class AdicionarGestor(forms.ModelForm):
    class Meta:
        model = Gestor
        fields = 'nome', 'email'
        verbose_name = 'Adicionar Gestor'
        relation = 'instituicao'
        can_view = 'Administrador',


class AdicionarPergunta(forms.ModelForm):
    class Meta:
        model = Pergunta
        verbose_name = 'Adicionar Pergunta'
        relation = 'categoria'
        exclude = ()
        fieldsets = {
            'Dados Gerais': ('ordem', 'pergunta', 'texto', 'tipo_resposta', 'obrigatoria'),
            'Opções de Resposta': ('opcoes',)
        }
        can_view = 'Administrador',


class AdicionarCampus(forms.ModelForm):
    class Meta:
        model = Campus
        fields = 'nome',
        verbose_name = 'Adicionar Campus'
        relation = 'instituicao'
        can_view = 'Administrador',


class AlterarPrioridade(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = 'prioridade',
        verbose_name = 'Alterar Prioridade'
        can_view = 'Gestor',

    def can_view(self, user):
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


class NaoInformarDemanda(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = ()
        verbose_name = 'Não Informar'
        style = 'danger'
        can_view = 'Gestor',

    def save(self, *args, **kwargs):
        self.instance.valor = 0
        self.instance.valor_total = 0
        self.instance.descricao = 'Não Informado'
        self.instance.finalizada = True
        super().save(*args, **kwargs)

    def can_view(self, user):
        return self.instance.ciclo.is_aberto() and not self.instance.finalizada


class PreencherDemanda(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = 'classificacao', 'prioridade', 'descricao', 'valor_total', 'valor', 'unidades_beneficiadas'
        verbose_name = 'Preencher Dados Gerais'
        can_view = 'Gestor',

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        disponivel = self.instance.ciclo.teto - self.instance.ciclo.demanda_set.filter(instituicao=self.instance.instituicao).exclude(pk=self.instance.pk).exclude(classificacao__contabilizar=False).sum('valor')
        self.fields['classificacao'].widget.attrs.update(readonly='readonly')
        self.fields['prioridade'].widget.attrs.update(readonly='readonly')
        self.fields['valor'].help_text = 'Valor Disponível R$: {}'.format(format_value(disponivel))

    def can_view(self, user):
        return self.instance.ciclo.is_aberto() and not self.instance.finalizada

    def clean_valor_total(self):
        valor_total = self.cleaned_data['valor_total']
        if valor_total < 176000:
            raise forms.ValidationError('O valor deve ser maior que R$ 176.000,00')
        return valor_total

    def clean_valor(self):
        valor = self.cleaned_data['valor']
        total = self.instance.ciclo.demanda_set.filter(instituicao=self.instance.instituicao).exclude(pk=self.instance.pk).exclude(classificacao__contabilizar=False).sum('valor')
        if self.instance.classificacao.contabilizar and total + valor > self.instance.ciclo.teto:
            raise forms.ValidationError(
                'Esse valor faz com que o limite de investimento para a instituição seja ultrapassado.')
        if valor < 176000:
            raise forms.ValidationError('O valor deve ser maior que R$ 176.000,00')
        return valor

    def get_unidades_beneficiadas_queryset(self, queryset):
        return queryset.role_lookups('Gestor', instituicao='instituicao').apply_role_lookups(self.request.user)


class AlterarPreenchimento(PreencherDemanda):
    class Meta:
        model = Demanda
        fields = 'classificacao', 'prioridade', 'descricao', 'valor_total', 'valor', 'unidades_beneficiadas'
        verbose_name = 'Alterar Dados Gerais'
        can_view = 'Gestor',


class Reabir(forms.ModelForm):
    class Meta:
        model = Demanda
        verbose_name = 'Reabir para Edição'
        can_view = 'Administrador',

    def save(self, *args, **kwargs):
        self.instance.finalizada = False
        QuestionarioFinal.objects.filter(
            ciclo=self.instance.ciclo, instituicao=self.instance.instituicao
        ).update(finalizado=False)
        super().save(*args, **kwargs)


class DetalharDemanda(forms.ModelForm):

    class Meta:
        model = Demanda
        verbose_name = 'Detalhar Demanda'
        fields = []

    def can_view(self, user):
        return self.instance.ciclo.is_aberto() and user.roles.filter(name='Gestor').exists() and self.instance.get_questionario() is not None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for pergunta_questionario in self.instance.get_questionario().respostaquestionario_set.all().order_by('pergunta__ordem'):
            tipo_resposta = pergunta_questionario.pergunta.tipo_resposta
            key = '{}'.format(pergunta_questionario.pk)
            self.initial[key] = pergunta_questionario.resposta
            if tipo_resposta == Pergunta.TEXTO_CURTO:
                self.fields[key] = forms.CharField(
                    label=str(pergunta_questionario.pergunta),
                    required=False
                )
            elif tipo_resposta == Pergunta.TEXTO_LONGO:
                self.fields[key] = forms.CharField(
                    label=str(pergunta_questionario.pergunta), widget=forms.Textarea(),
                    required=False
                )
            elif tipo_resposta == Pergunta.NUMERO_DECIMAL:
                self.fields[key] = forms.DecimalField(
                    label=str(pergunta_questionario.pergunta),
                    required=False, localize=True
                )
            elif tipo_resposta == Pergunta.NUMERO_INTEIRO:
                self.fields[key] = forms.IntegerField(
                    label=str(pergunta_questionario.pergunta),
                    required=False
                )
            elif tipo_resposta == Pergunta.DATA:
                self.fields[key] = forms.DateField(
                    label=str(pergunta_questionario.pergunta),
                    required=False
                )
            elif tipo_resposta == Pergunta.BOOLEANO:
                self.fields[key] = forms.ChoiceField(
                    label=str(pergunta_questionario.pergunta),
                    required=False,
                    choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']]
                )
            elif tipo_resposta == Pergunta.ARQUIVO:
                self.fields[key] = forms.FileField(
                    label=str(pergunta_questionario.pergunta),
                    required=False,
                )
            elif tipo_resposta == Pergunta.OPCOES:
                self.fields[key] = forms.ChoiceField(
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

    def process(self):
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
        self.notify(reload=reload)


class AlterarDetalhamentoDemanda(DetalharDemanda):

    class Meta:
        model = Demanda
        verbose_name = 'Alterar Detalhamento'
        fields = []

    def can_view(self, user):
        if self.instance.valor and user.roles.filter(name='Gestor').exists():
            questionario_final = QuestionarioFinal.objects.filter(
                ciclo=self.instance.ciclo, instituicao=self.instance.instituicao
            )
            return self.instance.ciclo.is_aberto() and not questionario_final.filter(finalizado=True).exists()
        return False


class AlterarSenha(forms.Form):
    password = forms.CharField(label='Senha', widget=forms.PasswordInput())

    class Meta:
        verbose_name = 'Alterar Senha'

    def proces(self):
        self.instantiator.user.set_password(self.cleaned_data['password'])
        self.instantiator.user.save()


class ConcluirSolicitacao(forms.Form):

    rco_pendente = forms.ChoiceField(
        label='A instituição possui RCO pendente de entrega para a SETEC?',
        choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']],
    )
    detalhe_rco_pendente = forms.CharField(
        label='Número do(s) TED(s) e o resumo da situação caso possua RCO pendente de entregue para a SETEC',
        required=False, widget=forms.Textarea()
    )
    devolucao_ted = forms.ChoiceField(
        label='A instituição devolveu algum valor de TED em 2021?',
        choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']],
    )
    detalhe_devolucao_ted = forms.CharField(
        label='Número do(s) TED(s) e o resumo da situação caso tenha devolvido algum valor de TED em 2021',
        required=False, widget=forms.Textarea()
    )
    prioridade_1 = forms.ModelChoiceField(Demanda.objects, label='Prioridade 1', help_text='Dentre as demandas informadas, elenque a 1ª mais prioritária para este exercício.')
    prioridade_2 = forms.ModelChoiceField(Demanda.objects, label='Prioridade 2', help_text='Dentre as demandas informadas, elenque a 2ª mais prioritária para este exercício.')
    prioridade_3 = forms.ModelChoiceField(Demanda.objects, label='Prioridade 3', help_text='Dentre as demandas informadas, elenque a 3ª mais prioritária para este exercício.')

    class Meta:
        verbose_name = 'Concluir Solicitação'
        can_view = 'Gestor',
        style = 'success'
        fieldsets = {
            'Demandas Prioritárias do Exercício': ('prioridade_1', 'prioridade_2', 'prioridade_3'),
            'Relatório de Cumprimento do Objeto (RCO)': ('rco_pendente', 'detalhe_rco_pendente'),
            'Transferência Eletrônica Descentralizada (TED)': ('devolucao_ted', 'detalhe_devolucao_ted'),
        }

    def __init__(self, *args, **kwargs):
        initial = {}
        gestor = Gestor.objects.filter(user=kwargs['request'].user).first()
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

    def can_view(self, user):
        if user.roles.filter(name='Gestor').exists():
            gestor = Gestor.objects.filter(user=user).first()
            ciclo = self.instantiator
            instituicao = gestor.instituicao
            demandas_finalizadas = not Demanda.objects.filter(ciclo=ciclo, instituicao=instituicao, finalizada=False).exists()
            questionario_final = QuestionarioFinal.objects.filter(ciclo=ciclo, instituicao=instituicao, finalizado=True).first()
            return demandas_finalizadas and not questionario_final
        return False

    def process(self):
        gestor = Gestor.objects.filter(user=self.request.user).first()
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
        self.notify('Solicitação concluída com sucesso.')


class DuvidaForm(forms.ModelForm):
    class Meta:
        model = Duvida
        verbose_name = 'Tirar Dúvida'
        fields = 'pergunta',

    def can_view(self, user):
        if user.roles.filter(name='Gestor').exists():
            return True
        return False

    def save(self, *args, **kwargs):
        gestor = Gestor.objects.filter(user=self.request.user).first()
        self.instance.data_pergunta = datetime.now()
        self.instance.instituicao = gestor.instituicao
        return super().save(*args, **kwargs)


class ResponderDuvida(forms.ModelForm):
    class Meta:
        model = Duvida
        verbose_name = 'Responder Dúvida'
        fields = 'resposta',

    def can_view(self, user):
        if user.roles.filter(name='Administrador').exists():
            return True
        return False

    def save(self, *args, **kwargs):
        self.instance.data_resposta = datetime.now()
        return super().save(*args, **kwargs)


class RestaurarDemanda(forms.ModelForm):
    class Meta:
        model = Demanda
        verbose_name = 'Restaurar'
        fields = ()
        style = 'danger'

    def can_view(self, user):
        if user.roles.filter(name='Administrador').exists() and self.instance.descricao:
            return True
        return False

    def save(self, *args, **kwargs):
        self.instance.descricao = ''
        self.instance.valor = None
        self.instance.valor_total = None
        return super().save(*args, **kwargs)


class ExportarResultado(forms.Form):

    instituicao = forms.ModelChoiceField(Instituicao.objects, label='Instituição', required=False)
    categoria = forms.ModelChoiceField(Categoria.objects, label='Categoria', required=False)
    prioridade = forms.ModelChoiceField(Prioridade.objects, label='Prioridade', required=False)

    class Meta:
        verbose_name = 'Exportar Resultado'
        can_view = 'Administrador',
        icon = 'bi-file-exce'

    def process(self):
        dados = list()
        demandas = list([['DEMANDA', 'CATEGORIA', 'INSTITUIÇÃO', 'UNIDADES BENEFICIADAS', 'PRIORIDADE', 'VALOR TOTAL', 'VALOR EMPENHO']])
        questionario = list([['DEMANDA', 'CATEGORIA', 'INSTITUIÇÃO', 'PRIORIDADE', 'VALOR TOTAL', 'VALOR EMPENHO', 'PERGUNTA', 'RESPOSTA']])
        fechamento = list([['INSTITUIÇÃO', 'PERGUNTA', 'RESPOSTA']])
        prioridades = list([['INSTITUIÇÃO', 'PRIORIDADES', 'DEMANDA']]) 
        dados.append(('Demandas', demandas))
        dados.append(('Questionário', questionario))
        dados.append(('Fechamento', fechamento))
        dados.append(('Prioridades', prioridades))
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
                    prioridades.append([instituicao1.sigla, 1, questionario_final.prioridade_1.descricao if questionario_final.prioridade_1.descricao else ''])
                    prioridades.append([instituicao1.sigla, 2, questionario_final.prioridade_2.descricao if questionario_final.prioridade_2.descricao else ''])
                    prioridades.append([instituicao1.sigla, 3, questionario_final.prioridade_3.descricao if questionario_final.prioridade_3.descricao else ''])
        self.http_response(XlsResponse(dados))


class ExportarResultadoPorCategoria(forms.Form):

    instituicao = forms.ModelChoiceField(Instituicao.objects, label='Instituição', required=False)
    categoria = forms.ModelChoiceField(Categoria.objects, label='Categoria', required=False)
    prioridade = forms.ModelChoiceField(Prioridade.objects, label='Prioridade', required=False)

    class Meta:
        verbose_name = 'Exportar Resultado por Categoria'
        can_view = 'Administrador',
        icon = 'bi-file-exce'

    def process(self):
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
