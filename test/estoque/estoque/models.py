from sloth.db import models
from sloth.decorators import role


class PessoaManager(models.Manager):
    def all(self):
        return self


class Pessoa(models.Model):

    nome = models.CharField(verbose_name='Nome')
    email = models.EmailField(verbose_name='E-mail')

    objects = PessoaManager()

    class Meta:
        verbose_name = 'Pessoa'
        verbose_name_plural = 'Pessoas'

    def __str__(self):
        return self.nome


class RedeManager(models.Manager):
    def all(self):
        return self.role_lookups('Gerente de Rede', pk='rede').dynamic_filters('gerente')


@role('Gerente de Rede', username='gerente__email')
class Rede(models.Model):

    nome = models.CharField(verbose_name='Nome')
    gerente = models.ForeignKey(Pessoa, verbose_name='Gerente', null=True, blank=True)

    objects = RedeManager()

    class Meta:
        verbose_name = 'Rede'
        verbose_name_plural = 'Redes'

    def __str__(self):
        return self.nome

    def get_dados_gerais(self):
        return self.values('nome')

    def get_dados_gerente(self):
        return self.gerente.values('nome', 'email') if self.gerente else self.values('gerente')

    def get_lojas(self):
        return self.loja_set.global_actions('AdicionarLoja')

    def get_detalhamento(self):
        return self.values('get_dados_gerente', 'get_dados_lojas')

    def get_total_loja_por_rede(self):
        return self.loja_set.count('rede')

    def get_dados_lojas(self):
        return self.values('get_lojas', 'get_total_loja_por_rede')

    def view(self):
        return self.values('get_dados_gerais', 'get_lojas', 'get_detalhamento')

    def has_list_permission(self, user):
        return user.roles.contains('Gerente de Rede')


class LojaManager(models.Manager):
    def all(self):
        return self


class Loja(models.Model):

    nome = models.CharField(verbose_name='Nome')
    rede = models.ForeignKey(Rede, verbose_name='Rede', null=True, blank=True)

    objects = LojaManager()

    class Meta:
        verbose_name = 'Loja'
        verbose_name_plural = 'Lojas'

    def __str__(self):
        return self.nome

