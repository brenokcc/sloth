# -*- coding: utf-8 -*-

from django import forms

from .models import Servidor, Ferias, Estado


class FazerAlgumaCoisa(forms.Form):
    mensagem = forms.CharField(label='Mensagem', widget=forms.Textarea())


class EditarSiglaEstado(forms.QuerySetForm):
    class Meta:
        name = 'Editar Sigla'
        model = Estado
        fields = 'sigla',


class EditarSiglasEstado(forms.QuerySetForm):
    class Meta:
        name = 'Editar Siglas'
        model = Estado
        fields = 'sigla',
        batch = True


class CorrigirNomeServidor1(forms.ModelForm):
    class Meta:
        name = 'Corrigir Nome'
        model = Servidor
        fields = 'nome',


class CorrigirNomeServidor(forms.QuerySetForm):
    class Meta:
        name = 'Corrigir Nome'
        model = Servidor
        fields = 'nome',


class EditarFerias(forms.QuerySetForm):
    class Meta:
        name = 'Editar'
        model = Ferias
        exclude = ()


class AtivarServidor(forms.QuerySetForm):
    class Meta:
        name = 'Ativar'
        model = Servidor
        fields = ()


class InativarServidores(forms.QuerySetForm):
    class Meta:
        title = 'Inativar'
        model = Servidor
        batch = True
        fields = ()

    def save(self):
        self.instance.ativo = False
        super().save()


class InformarEndereco(forms.ModelForm):
    class Meta:
        model = Servidor
        field = 'endereco'
        name = 'Informar'
        icon = 'archive'
        style = 'success'
        fields = 'endereco',


class ExcluirEndereco(forms.ModelForm):
    class Meta:
        name = 'Excluir'
        model = Servidor
        fields = ()

    def process(self):
        self.instance.endereco.delete()


class CadastrarFerias(forms.ModelForm):
    class Meta:
        name = 'Cadastrar'
        model = Ferias
        exclude = ()


class AlterarFerias(forms.QuerySetForm):
    class Meta:
        name = 'Alterar'
        model = Ferias
        fields = 'inicio', 'fim'


class ExcluirFerias(forms.QuerySetForm):
    class Meta:
        name = 'Excluir'
        model = Ferias
        exclude = ()
        batch = True
