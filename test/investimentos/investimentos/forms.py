# -*- coding: utf-8 -*-

from sloth import forms
from sloth.utils.formatter import format_value

from .models import Campus, Demanda, Pergunta, Gestor, PerguntaQuestionario


class AdicionarGestor(forms.ModelForm):
    class Meta:
        model = Gestor
        fields = 'nome', 'cpf'
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
        fields = 'nome', 'sigla'
        verbose_name = 'Adicionar Campus'
        relation = 'instituicao'
        can_view = 'Administrador',


class AlterarPrioridade(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = 'prioridade',
        verbose_name = 'Alterar Prioridade'
        can_view = 'Gestor',

    def get_prioridade_queryset(self, queryset):
        return queryset.filter(
            numero__lte=self.instance.ciclo.get_limite_demandas()
        ).exclude(numero=self.instance.prioridade.numero)


class DetalharDemanda(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = 'descricao', 'classificacao', 'valor'
        verbose_name = 'Detalhar Demanda'
        can_view = 'Gestor',

    def can_view(self, user):
        return not self.instance.finalizada

    def clean_valor(self):
        valor = self.cleaned_data['valor']
        instituicao = self.instance.instituicao
        total = self.instance.ciclo.demanda_set.filter(instituicao=instituicao).exclude(pk=self.instance.pk).sum('valor')
        if total + valor > self.instance.ciclo.teto:
            raise forms.ValidationError(
                'Esse valor faz com que o limite de investimento para a instituição seja ultrapassado.')
        return valor

    def get_classificacao_queryset(self, queryset):
        pks = []
        for limite in self.instance.ciclo.limites.all():
            instituicao = self.instance.instituicao
            n = self.instance.ciclo.demanda_set.filter(instituicao=instituicao).filter(
                classificacao=limite.classificacao).exclude(pk=self.instance.pk).count()
            print(limite, n, 888)
            if n < limite.quantidade:
                pks.append(limite.classificacao.id)
        return queryset.filter(pk__in=pks)


class CancelarFinalizacao(forms.ModelForm):
    class Meta:
        model = Demanda
        verbose_name = 'Cancelar Finalização'
        can_view = 'Gestor',

    def save(self, *args, **kwargs):
        self.instance.finalizada = False
        super().save(*args, **kwargs)


class ResponderQuestionario(forms.ModelForm):

    class Meta:
        model = Demanda
        verbose_name = 'Responder Questionário'
        fields = []

    def can_view(self, user):
        return user.roles.filter(name='Gestor').exists() and self.instance.get_questionario() is not None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for pergunta_questionario in self.instance.get_questionario().perguntaquestionario_set.all():
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
                    required=False
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
                self.fields[key] = forms.BooleanField(
                    label=pergunta_questionario.pergunta.texto,
                    required=False
                )
            elif tipo_resposta == Pergunta.OPCOES:
                self.fields[key] = forms.ChoiceField(
                    label=pergunta_questionario.pergunta.texto,
                    required=False,
                    choices=[[str(x), str(x)] for x in pergunta_questionario.pergunta.opcoes.all()]
                )

    def get_fieldsets(self):
        return {
            'Perguntas': list(self.fields.keys())
        }

    def process(self):
        for pergunta_questionario in self.instance.get_questionario().perguntaquestionario_set.all():
            key = '{}'.format(pergunta_questionario.pk)
            resposta = format_value(self.cleaned_data[key]) if self.cleaned_data[key] else None
            pergunta_questionario.resposta = resposta
            pergunta_questionario.save()
        if self.instance.get_progresso_questionario() == 100:
            self.instance.finalizada = True
            self.instance.save()
        self.notify()


class AlterarSenha(forms.Form):
    password = forms.CharField(label='Senha', widget=forms.PasswordInput())

    class Meta:
        verbose_name = 'Alterar Senha'

    def proces(self):
        self.instantiator.user.set_password(self.cleaned_data['password'])
        self.instantiator.user.save()
