from dms2 import forms
from .models import Servidor, Ferias


class CorrigirNomeServidor(forms.ModelForm):
    class Meta:
        name = 'Corrigir Nome'
        model = Servidor
        fields = 'nome',


class FazerAlgumaCoisa(forms.Form):
    pass


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
        fields = ()


class InformarEndereco(forms.ModelForm):
    class Meta:
        model = Servidor
        field = 'endereco'
        name = 'Informar'
        icon = 'address'
        style = 'success'
        fields = 'endereco',


class ExcluirEndereco(forms.ModelForm):
    class Meta:
        name = 'Excluir'
        model = Servidor
        fields = ()

    def submit(self):
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
        exclude = ()


class ExcluirFerias(forms.QuerySetForm):
    class Meta:
        name = 'Excluir'
        model = Ferias
        exclude = ()
        batch = True
