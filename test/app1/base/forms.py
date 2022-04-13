# -*- coding: utf-8 -*-

from sloth import forms

from .models import Servidor, Ferias, Estado, Frequencia, Municipio


class AdicionarMunicipioEstado(forms.ModelForm):

    class Meta:
        model = Municipio
        exclude = ()
        relation = 'estado'
        verbose_name = 'Adicionar Município'


class HomologarFrequencia(forms.ModelForm):
    class Meta:
        verbose_name = 'Homologar'
        model = Frequencia
        fields = 'homologado',


class RegistrarPonto(forms.ModelForm):

    class Meta:
        model = Frequencia
        fields = 'horario', 'homologado',
        relation = 'servidor'


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
            'Dados Gerais': ('nome', 'foto', ('cpf', 'matricula', 'data_nascimento', 'naturalidade'), 'ativo'),
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
        style = 'warning'


class EditarSiglaEstado(forms.ModelForm):
    class Meta:
        verbose_name = 'Editar Sigla'
        model = Estado
        fields = 'sigla',


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
        fields = 'inicio', 'fim'


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


class ExcluirEndereco(forms.ModelForm):
    class Meta:
        verbose_name = 'Excluir'
        model = Servidor
        fields = ()

    def save(self):
        self.instance.endereco.delete()
        self.redirect(message='Endereço excluído com sucesso.')


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
