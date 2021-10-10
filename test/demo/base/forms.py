from dms2 import forms
from .models import Servidor, Endereco, Ferias


class AtivarServidor(forms.InstanceForm):
    class Meta:
        model = Servidor
        fields = ()


class InativarServidores(forms.QuerySetForm):
    class Meta:
        model = Servidor
        fields = ()


class InformarEndereco(forms.ModelForm):
    class Meta:
        model = Endereco
        exclude = ()


class EditarEndereco(forms.InstanceForm):
    class Meta:
        model = Endereco
        exclude = ()


class ExcluirEndereco(forms.InstanceForm):
    class Meta:
        model = Endereco
        exclude = ()


class CadastrarFerias(forms.ModelForm):
    class Meta:
        model = Ferias
        exclude = ()


class EditarFerias(forms.InstanceForm):
    class Meta:
        model = Ferias
        exclude = ()


class ExcluirFerias(forms.InstanceForm):
    class Meta:
        model = Ferias
        exclude = ()
