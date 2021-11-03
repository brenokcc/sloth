# -*- coding: utf-8 -*-

from dms2 import forms

from .models import Servidor, Ferias, Estado


class EstadoForm(forms.ModelForm):
    class Meta:
        name = 'Cadastrar Estado'
        model = Estado
        exclude = ()

    fieldsets = {
        'Dados Gerais': ('sigla',),
        'Endereço': ('endereco',),
    }


class ServidorForm(forms.ModelForm):

    fieldsets = {
        'Dados Gerais': ('nome', ('matricula', 'data_nascimento'), ('nome', 'cpf', 'nome')),
        'Outros Dados': (('nome', 'cpf', 'nome', 'naturalidade'),),
        'Endereço': ('endereco',),
    }

    class Meta:
        name = 'Cadastrar Servidor'
        model = Servidor
        exclude = ()


class InformarCidadesMetropolitanas(forms.ModelForm):

    class Meta:
        model = Estado
        fields = 'cidades_metropolitanas',
        name = 'Informar Cidades Metropolitanas'
        submit = 'Informar'

    def get_cidades_metropolitanas_queryset(self, queryset):
        return queryset.filter(estado=self.instance)


class FazerAlgumaCoisa(forms.Form):
    mensagem = forms.CharField(label='Mensagem', widget=forms.Textarea())

    def has_permission(self):
        return True


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

    def save(self):
        self.instance.ativo = True
        super().save()


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

    def has_permission(self):
        return super().has_permission()


class ExcluirEndereco(forms.ModelForm):
    class Meta:
        name = 'Excluir'
        model = Servidor
        fields = ()

    def save(self):
        self.instance.endereco.delete()
        self.notify()

    def has_permission(self):
        return True


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
