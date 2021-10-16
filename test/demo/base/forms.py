from dms2 import forms
from .models import Servidor, Endereco, Ferias


class CorrigirNome(forms.ModelForm):
    class Meta:
        model = Servidor
        fields = 'nome',


class EditarFerias(forms.InstanceForm):
    class Meta:
        name = 'Editar'
        model = Ferias
        exclude = ()


class AtivarServidor(forms.InstanceForm):
    class Meta:
        name = 'Ativar'
        model = Servidor
        fields = ()


class InativarServidores(forms.QuerySetForm):
    class Meta:
        title = 'Inativar'
        model = Servidor
        fields = ()


class InformarEndereco(forms.ModelForm):
    class Meta:
        model = Endereco
        exclude = ()
        name = 'Informar'
        icon = 'address'
        style = 'success'


class EditarEndereco(forms.InstanceForm):
    class Meta:
        name = 'Editar'
        model = Endereco
        exclude = ()


class ExcluirEndereco(forms.InstanceForm):
    class Meta:
        name = 'Excluir'
        model = Endereco
        exclude = ()


class CadastrarFerias(forms.ModelForm):
    class Meta:
        name = 'Cadastrar'
        model = Ferias
        exclude = ()


class AlterarFerias(forms.InstanceForm):
    class Meta:
        name = 'Alterar'
        model = Ferias
        exclude = ()


class ExcluirFerias(forms.QuerySetForm):
    class Meta:
        name = 'Excluir'
        model = Ferias
        exclude = ()
