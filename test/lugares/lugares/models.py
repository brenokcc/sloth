from sloth.db import models, role, meta


class PaisManager(models.Manager):
    def all(self):
        return self.display('nome', 'get_total_estados')


class Pais(models.Model):

    nome = models.CharField('Nome')

    objects = PaisManager()

    class Meta:
        verbose_name = 'País'
        verbose_name_plural = 'Países'

    def __str__(self):
        return self.nome

    def get_dados_gerais(self):
        return self.value_set('nome')

    def get_estados(self):
        return self.estado_set.ignore('pais').expand().actions('view', 'edit', 'delete')

    @meta('Total de Estados', renderer='badges/primary')
    def get_total_estados(self):
        return self.get_estados().count()

    def view(self):
        return self.value_set('get_dados_gerais', 'get_estados')


class EstadoManager(models.Manager):
    def all(self):
        return self


class Estado(models.Model):
    pais = models.ForeignKey(Pais, verbose_name='País')
    nome = models.CharField('Nome')

    objects = EstadoManager()

    class Meta:
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'

    def __str__(self):
        return self.nome

    def get_dados_gerais(self):
        return self.value_set('nome')

    def get_cidades(self):
        return self.cidade_set.all().ignore('estado').expand().actions('view', 'edit', 'delete').global_actions('adicionar_cidade')

    def view(self):
        return self.value_set('get_dados_gerais', 'get_cidades')


class CidadeManager(models.Manager):
    def all(self):
        return self.display('get_foto', 'nome')


class Cidade(models.Model):
    foto = models.ImageField('Foto', upload_to='cidades')
    estado = models.ForeignKey(Estado, verbose_name='Estado')
    nome = models.CharField('Nome')

    objects = CidadeManager()

    class Meta:
        verbose_name = 'Cidade'
        verbose_name_plural = 'Cidades'

    def __str__(self):
        return self.nome

    @meta('Foto', renderer='images/image')
    def get_foto(self):
        return self.foto

    def get_dados_gerais(self):
        return self.value_set('nome', 'get_total_pessoas').image('foto')

    def get_pessoas(self):
        return self.pessoa_set.ignore('cidade').actions('delete')

    def get_total_pessoas(self):
        return self.pessoa_set.count()

    def get_total_pessoas_por_sexo(self):
        return self.pessoa_set.count('sexo').donut_chart()

    def get_total_pessoas_casadas(self):
        return self.pessoa_set.count('casado').column_chart()

    def get_estatisticas(self):
        return self.value_set('get_total_pessoas_por_sexo', 'get_total_pessoas_casadas')

    def get_homens(self):
        return self.get_pessoas().homens()

    def get_mulheres(self):
        return self.get_pessoas().mulheres().global_actions('fazer_alguma_coisa')

    def get_habitantes(self):
        return self.value_set('get_homens', 'get_mulheres')

    def get_dados_estado(self):
        return self.estado.get_dados_gerais()

    def view(self):
        return self.value_set('get_dados_gerais', 'get_habitantes', 'get_dados_estado').append('get_total_pessoas_por_sexo', 'get_total_pessoas_casadas').attach('get_estatisticas')


class PessoaManager(models.Manager):
    def all(self):
        return self

    def homens(self):
        return self.filter(sexo='M').preview('get_dados_gerais')

    def mulheres(self):
        return self.filter(sexo='F').preview('get_dados_gerais')


class Pessoa(models.Model):
    cidade = models.ForeignKey(Cidade, verbose_name='Cidade')
    nome = models.CharField('Nome')
    sexo = models.CharField('Sexo', choices=[['M', 'M'], ['F', 'F']])
    data_nascimento = models.DateField('Data de Nascimento')
    casado = models.BooleanField('Casado', default=False)

    objects = PessoaManager()

    class Meta:
        verbose_name = 'Pessoa'
        verbose_name_plural = 'Pessoas'

    def __str__(self):
        return self.nome

    def get_dados_gerais(self):
        return self.value_set('nome', ('sexo', 'data_nascimento'))
