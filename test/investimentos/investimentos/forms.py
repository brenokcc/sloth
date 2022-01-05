# -*- coding: utf-8 -*-
import os
from datetime import datetime

from django.conf import settings
from sloth import forms
from sloth.utils.formatter import format_value

from .models import Campus, Demanda, Pergunta, Gestor, QuestionarioFinal, Duvida


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
            'Dados Gerais': ('texto', 'tipo_resposta', 'obrigatoria'),
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
        return self.instance.classificacao is not None and not self.instance.finalizada and self.instance.prioridade.numero > 1

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
        return not self.instance.finalizada


class PreencherDemanda(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = 'descricao', 'valor_total', 'valor', 'unidades_beneficiadas'
        verbose_name = 'Preencher Dados Gerais'
        can_view = 'Gestor',

    def can_view(self, user):
        return not self.instance.finalizada

    def clean_valor_total(self):
        valor_total = self.cleaned_data['valor_total']
        if valor_total < 176000:
            raise forms.ValidationError('O valor deve ser maior que R$ 176.000,00')
        return valor_total

    def clean_valor(self):
        valor = self.cleaned_data['valor']
        instituicao = self.instance.instituicao
        total = self.instance.ciclo.demanda_set.filter(instituicao=instituicao).exclude(pk=self.instance.pk).exclude(classificacao__contabilizar=False).sum('valor')
        if total + valor > self.instance.ciclo.teto:
            raise forms.ValidationError(
                'Esse valor faz com que o limite de investimento para a instituição seja ultrapassado.')
        if False and valor < 176000:
            raise forms.ValidationError('O valor deve ser maior que R$ 176.000,00')
        return valor

    def get_unidades_beneficiadas_queryset(self, queryset):
        return queryset.role_lookups('Gestor', instituicao='instituicao').apply_role_lookups(self.request.user)


class AlterarPreenchimento(PreencherDemanda):
    class Meta:
        model = Demanda
        fields = 'descricao', 'valor', 'unidades_beneficiadas'
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
        return user.roles.filter(name='Gestor').exists() and self.instance.get_questionario() is not None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for pergunta_questionario in self.instance.get_questionario().respostaquestionario_set.all().order_by('id'):
            tipo_resposta = pergunta_questionario.pergunta.tipo_resposta
            key = '{}'.format(pergunta_questionario.pk)
            self.initial[key] = pergunta_questionario.resposta
            if tipo_resposta == Pergunta.TEXTO_CURTO:
                self.fields[key] = forms.CharField(
                    label=pergunta_questionario.pergunta.texto,
                    required=False
                )
            elif tipo_resposta == Pergunta.TEXTO_LONGO:
                self.fields[key] = forms.CharField(
                    label=pergunta_questionario.pergunta.texto, widget=forms.Textarea(),
                    required=False
                )
            elif tipo_resposta == Pergunta.NUMERO_DECIMAL:
                self.fields[key] = forms.DecimalField(
                    label=pergunta_questionario.pergunta.texto,
                    required=False, localize=True
                )
            elif tipo_resposta == Pergunta.NUMERO_INTEIRO:
                self.fields[key] = forms.IntegerField(
                    label=pergunta_questionario.pergunta.texto,
                    required=False
                )
            elif tipo_resposta == Pergunta.DATA:
                self.fields[key] = forms.DateField(
                    label=pergunta_questionario.pergunta.texto,
                    required=False
                )
            elif tipo_resposta == Pergunta.BOOLEANO:
                self.fields[key] = forms.ChoiceField(
                    label=pergunta_questionario.pergunta.texto,
                    required=False,
                    choices=[['', ''], ['Sim', 'Sim'], ['Não', 'Não']]
                )
            elif tipo_resposta == Pergunta.ARQUIVO:
                self.fields[key] = forms.FileField(
                    label=pergunta_questionario.pergunta.texto,
                    required=False,
                )
            elif tipo_resposta == Pergunta.OPCOES:
                self.fields[key] = forms.ChoiceField(
                    label=pergunta_questionario.pergunta.texto,
                    required=False,
                    choices=[['', '']] + [[str(x), str(x)] for x in pergunta_questionario.pergunta.opcoes.all()]
                )

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
            return not questionario_final.filter(finalizado=True).exists()
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
        label='A instituição possui RCO pendente de entregue para a SETEC?',
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
        label='Número do(s) TED(s) e o resumo da situação caso tenha devolvido algum valor de TED em 2021?',
        required=False, widget=forms.Textarea()
    )

    class Meta:
        verbose_name = 'Concluir Solicitação'
        can_view = 'Gestor',
        style = 'success'

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
            )
        kwargs.update(initial=initial)
        super().__init__(*args, **kwargs)

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
