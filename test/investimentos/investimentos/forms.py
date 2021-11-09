# -*- coding: utf-8 -*-

from sloth import forms

from .models import Subcategoria, Campus, Demanda, Instituicao, Prioridade, Pergunta


class AdicionarSubcategoria(forms.ModelForm):
    class Meta:
        model = Subcategoria
        fields = 'nome',
        verbose_name = 'Adicionar Subcategoria'
        relation = 'categoria'


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


class AdicionarCampus(forms.ModelForm):
    class Meta:
        model = Campus
        fields = 'nome', 'sigla'
        verbose_name = 'Adicionar Campus'
        relation = 'instituicao'


class AdicionarInstituicoesCiclo(forms.Form):
    instituicao = forms.ModelMultipleChoiceField(Instituicao.objects, label='Instituições')

    class Meta:
        model = Demanda
        fields = 'instituicao',
        verbose_name = 'Adicionar Instituições'

    def process(self):
        for instituicao in self.cleaned_data['instituicao']:
            for i in range(1, self.instantiator.prioridades+1):
                prioridade = Prioridade.objects.get_or_create(numero=i)[0]
                lookups = dict(ciclo=self.instantiator, instituicao=instituicao, prioridade=prioridade)
                if not Demanda.objects.filter(**lookups).exists():
                    Demanda.objects.create(**lookups)
        self.notify()


class DetalharDemanda(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = 'prioridade', 'classificacao', 'valor'
        verbose_name = 'Detalhar Demanda'


class InformarValorDemanda(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = 'valor',
        verbose_name = 'Informar Valor'


class ClassificarDemanda(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = 'classificacao',
        verbose_name = 'Classificar Demanda'
