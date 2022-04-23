# -*- coding: utf-8 -*-
from datetime import datetime
from sloth.db import models
from sloth.decorators import role, verbose_name, template


class DoencaManager(models.Manager):

    def all(self):
        return self.attach('contagiosas', 'nao_contagiosas')

    def contagiosas(self):
        return self.filter(contagiosa=True)

    def nao_contagiosas(self):
        return self.filter(contagiosa=False)


class Doenca(models.Model):
    descricao = models.CharField(verbose_name='Descrição')
    contagiosa = models.BooleanField(verbose_name='Contagiosa')

    objects = DoencaManager()

    class Meta:
        verbose_name = 'Doença'
        verbose_name_plural = 'Doenças'

    def __str__(self):
        return self.descricao


class TipoProcedimento(models.Model):
    descricao = models.CharField(verbose_name='Descrição')
    valor = models.DecimalField(verbose_name='Valor')

    class Meta:
        verbose_name = 'Tipo de Procedimento'
        verbose_name_plural = 'Tipos de Procedimento'

    def __str__(self):
        return self.descricao


class TipoAnimal(models.Model):
    descricao = models.CharField(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Tipo de Animal'
        verbose_name_plural = 'Tipos de Animais'

    def __str__(self):
        return self.descricao


@role('Funcionário', 'cpf')
class Funcionario(models.Model):

    nome = models.CharField(verbose_name='None')
    cpf = models.CharField(verbose_name='CPF')

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'

    def __str__(self):
        return self.nome


@role('Cliente', 'cpf')
class Cliente(models.Model):

    nome = models.CharField(verbose_name='None')
    cpf = models.CharField(verbose_name='CPF')

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return self.nome


class AnimalManager(models.Manager):

    def all(self):
        return self.template('adm/queryset/cards')

    def meus_animais(self):
        return self

    def get_qtd_por_tipo(self):
        return self.all().count('tipo')

    def get_qtd_por_periodo(self):
        return self.all().count('data_cadastro')


class Animal(models.Model):
    foto = models.ImageField(verbose_name='Foto', upload_to='animais')

    nome = models.CharField(verbose_name='Nome')
    tipo = models.ForeignKey(TipoAnimal, verbose_name='Tipo')

    descricao = models.TextField(verbose_name='Descrição')

    proprietario = models.ForeignKey(Cliente, verbose_name='Proprietário')
    data_cadastro = models.DateField(verbose_name='Data do Cadastro', default=datetime.today)

    objects = AnimalManager()

    class Meta:
        verbose_name = 'Animal'
        verbose_name_plural = 'Animais'
        fieldsets = {
            'Dados Gerais': (('nome', 'tipo'), 'foto', 'data_cadastro', 'descricao', 'proprietario'),
        }

    def __str__(self):
        return self.nome

    def get_dados_gerais(self):
        return self.values(('nome', 'tipo'), 'descricao').image('foto')

    def get_proprietario(self):
        return self.proprietario.values(('nome', 'cpf'))

    def get_tratamentos(self):
        return self.tratamento_set.ignore('animal').global_actions('IniciarTratamento')

    def view(self):
        return self.values('get_dados_gerais', 'get_proprietario', 'get_tratamentos')


class TratamentoManager(models.Manager):

    def em_tratamento(self):
        return self.filter(data_fim__isnull=True)


class Tratamento(models.Model):
    animal = models.ForeignKey(Animal, verbose_name='Animal')
    doenca = models.ForeignKey(Doenca, verbose_name='Doença')
    data_inicio = models.DateField(verbose_name='Data de Início')
    data_fim = models.DateField(verbose_name='Data de Término', null=True)
    eficaz = models.BooleanField(verbose_name='Eficaz', null=True)

    class Meta:
        verbose_name = 'Tratamento'
        verbose_name_plural = 'Tratamentos'
        fieldsets = {
            'Dados Gerais': (('animal', 'doenca'), ('data_inicio', 'data_fim')),
            'Resultado': ('eficaz',),
        }

    def __str__(self):
        return '{} - Tratamento de {} contra {}'.format(self.id, self.animal, self.doenca)

    def get_dados_gerais(self):
        return self.values(('animal', 'doenca'), ('data_inicio', 'data_fim'))

    def get_procedimentos(self):
        return self.procedimento_set.ignore('tratamento').global_actions('RegistrarProcedimento').actions('edit')

    def get_eficacia(self):
        return self.values('eficaz').actions('FinalizarTratamento')

    def view(self):
        return self.values('get_dados_gerais', 'get_procedimentos', 'get_eficacia')

    def pode_ser_finalizado(self):
        return not self.data_fim and self.procedimento_set.exists()

    def finalizar(self, data_fim, eficaz):
        self.data_fim = data_fim
        self.eficaz = eficaz
        self.save()

    def has_edit_permission(self, user):
        return not self.procedimento_set.exists()

    def has_delete_permission(self, user):
        return self.has_edit_permission(user)


class ProcedimentoManager(models.Manager):

    def get_valor_gasto(self):
        return self.sum('tipo__valor')


class Procedimento(models.Model):
    tratamento = models.ForeignKey(Tratamento, verbose_name='Tratamento')

    tipo = models.ForeignKey(TipoProcedimento, verbose_name='Tipo')
    data_hora = models.DateTimeField(verbose_name='Data/Hora')

    observacao = models.TextField(verbose_name='Observação', blank=True)

    objects = ProcedimentoManager()

    class Meta:
        verbose_name = 'Procedimento'
        verbose_name_plural = 'Procedimentos'
        fieldsets = {
            'Dados Gerais': ('tratamento', ('tipo', 'data_hora'),),
            'Outras Informações': ('observacao',),
        }

    def __str__(self):
        return 'Tratamento {}'.format(self.id)

    def has_edit_permission(self, user):
        return self.tratamento and self.tratamento.eficaz is None
