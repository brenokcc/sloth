# -*- coding: utf-8 -*-

from sloth import forms

from .models import Subcategoria, Campus, Demanda, Pergunta, Gestor


class AdicionarGestor(forms.ModelForm):
    class Meta:
        model = Gestor
        fields = 'nome', 'cpf'
        verbose_name = 'Adicionar Gestor'
        relation = 'instituicao'
        can_execute = 'Administrador',


class AdicionarSubcategoria(forms.ModelForm):
    class Meta:
        model = Subcategoria
        fields = 'nome',
        verbose_name = 'Adicionar Subcategoria'
        relation = 'categoria'
        can_execute = 'Administrador',


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
        can_execute = 'Administrador',


class AdicionarCampus(forms.ModelForm):
    class Meta:
        model = Campus
        fields = 'nome', 'sigla'
        verbose_name = 'Adicionar Campus'
        relation = 'instituicao'
        can_execute = 'Administrador',


class DetalharDemanda(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = 'prioridade', 'classificacao', 'valor'
        verbose_name = 'Detalhar Demanda'
        can_execute = 'Gestor',


class ResponderQuestionario(forms.ModelForm):

    class Meta:
        model = Demanda
        verbose_name = 'Responder Questionário'
        fields = []
        can_execute = 'Gestor',

    def has_permission(self):
        return self.instance.get_questionario() is not None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.fake:
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
            self.load_fieldsets()

    def get_fieldsets(self):
        return {
            'Perguntas': list(self.fields.keys())
        }

    def process(self):
        for pergunta_questionario in self.instance.get_questionario().perguntaquestionario_set.all():
            key = '{}'.format(pergunta_questionario.pk)
            pergunta_questionario.resposta = self.cleaned_data[key] or None
            pergunta_questionario.save()
        self.notify()


class AlterarSenha(forms.Form):
    password = forms.CharField(label='Senha', widget=forms.PasswordInput())

    class Meta:
        verbose_name = 'Alterar Senha'

    def proces(self):
        self.instantiator.user.set_password(self.cleaned_data['password'])
        self.instantiator.user.save()
