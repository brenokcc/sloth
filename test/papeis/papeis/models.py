from sloth.db import models, role, meta


@role('Funcionário', username='nome')
class Funcionario(models.Model):
    nome = models.CharField()


class Rede(models.Model):
    nome = models.CharField()


@role('Diretor', username='nome', rede='rede')
class Diretor(models.Model):
    rede = models.ForeignKey(Rede)
    nome = models.CharField()


@role('Gerente', username='gerente__nome', loja='pk', rede='rede')
@role('Funcionário', username='funcionarios__nome', loja='pk', rede='rede')
class Loja(models.Model):
    nome = models.CharField()
    rede = models.ForeignKey(Rede)
    gerente = models.ForeignKey(Funcionario, null=True)
    funcionarios = models.ManyToManyField(Funcionario, related_name='lojas')


class ProdutoManager(models.Manager):
    def all(self):
        return self.role_lookups(
            'Gerente', 'Funcionário', loja='loja'
        ).role_lookups('Diretor', loja__rede='rede')


class Produto(models.Model):
    nome = models.CharField()
    loja = models.ForeignKey(Loja)

    objects = ProdutoManager()



