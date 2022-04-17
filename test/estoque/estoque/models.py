from sloth.db import models, role


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
        return '{}'.format(self.nome)


class RedeManager(models.Manager):
    def all(self):
        return self.role_lookups('Gerente de Rede', pk='rede').dynamic_filters('gerente')


@role('Gerente de Rede', username='gerente__email')
class Rede(models.Model):

    nome = models.CharField(verbose_name='Nome')
    gerente = models.ForeignKey(Pessoa, verbose_name='Gerente', null=True)

    objects = RedeManager()

    class Meta:
        verbose_name = 'Rede'
        verbose_name_plural = 'Redes'

    class Permission:
        list = 'Gerente de Rede',

    def __str__(self):
        return '{}'.format(self.nome)

