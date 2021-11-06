# -*- coding: utf-8 -*-

from dms2 import forms

from .models import Servidor, Ferias, Estado


class DefinirSetor(forms.ModelForm):
    class Meta:
        model = Servidor
        fields = 'setor',


class EstadoForm(forms.ModelForm):
    class Meta:
        verbose_name = 'Cadastrar Estado'
        model = Estado
        fieldsets = {
            'Dados Gerais': ('sigla', 'endereco', 'telefones'),
        }


class ServidorForm(forms.ModelForm):

    class Meta:
        verbose_name = 'Cadastrar Servidor'
        model = Servidor
        fieldsets = {
            'Dados Gerais': ('nome', ('cpf', 'matricula', 'data_nascimento', 'naturalidade'), 'ativo'),
            'Endereço': ('endereco',),
        }


class InformarCidadesMetropolitanas(forms.ModelForm):

    class Meta:
        model = Estado
        fields = 'cidades_metropolitanas',
        verbose_name = 'Informar Cidades Metropolitanas'
        submit_label = 'Informar'

    def get_cidades_metropolitanas_queryset(self, queryset):
        return queryset.filter(estado=self.instance)


class FazerAlgumaCoisa(forms.Form):
    mensagem = forms.CharField(label='Mensagem', widget=forms.Textarea())

    class Meta:
        verbose_name = 'Fazer Alguma Coisa'
        submit_label = 'Enviar'
        style = 'warning'

    def has_permission(self):
        return True


class EditarSiglaEstado(forms.ModelForm):
    class Meta:
        verbose_name = 'Editar Sigla'
        model = Estado
        fields = 'sigla',


class EditarSiglasEstado(forms.ModelForm):
    class Meta:
        verbose_name = 'Editar Siglas'
        model = Estado
        fields = 'sigla',
        batch = True


class CorrigirNomeServidor1(forms.ModelForm):
    class Meta:
        verbose_name = 'Corrigir Nome'
        model = Servidor
        fields = 'nome',


class CorrigirNomeServidor(forms.ModelForm):
    class Meta:
        verbose_name = 'Corrigir Nome'
        model = Servidor
        fields = 'nome',


class EditarFerias(forms.ModelForm):
    class Meta:
        verbose_name = 'Editar'
        model = Ferias
        exclude = ()


class AtivarServidor(forms.ModelForm):
    class Meta:
        verbose_name = 'Ativar'
        model = Servidor
        fields = ()

    def save(self):
        self.instance.ativo = True
        super().save()


class InativarServidores(forms.ModelForm):
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
        verbose_name = 'Informar'
        icon = 'archive'
        style = 'success'
        fields = 'endereco',

    def has_permission(self):
        return super().has_permission()


class ExcluirEndereco(forms.ModelForm):
    class Meta:
        verbose_name = 'Excluir'
        model = Servidor
        fields = ()

    def save(self):
        self.instance.endereco.delete()
        self.notify()

    def has_permission(self):
        return True


class CadastrarFerias(forms.ModelForm):
    class Meta:
        verbose_name = 'Cadastrar'
        model = Ferias
        exclude = ()


class AlterarFerias(forms.ModelForm):
    class Meta:
        verbose_name = 'Alterar'
        model = Ferias
        fields = 'inicio', 'fim'


class ExcluirFerias(forms.ModelForm):
    class Meta:
        verbose_name = 'Excluir'
        model = Ferias
        exclude = ()
        batch = True
