from sloth.db import models
from sloth.decorators import role


class Pessoa(models.Model):
    nome = models.CharField(verbose_name='Nome', max_length=100)
    email = models.EmailField(verbose_name='E-mail', max_length=100)

    class Meta:
        abstract = True
        verbose_name = 'Pessoa'
        verbose_name_plural = 'Pessoas'

    def __str__(self):
        return self.nome


@role('Administrador', 'email')
class Administrador(Pessoa):

    class Meta:
        verbose_name = 'Administrador'
        verbose_name_plural = 'Administradores'


class EtapaEnsino(models.Model):

    nome = models.CharField(verbose_name='Nome')

    class Meta:
        verbose_name = 'Etada de Ensino'
        verbose_name_plural = 'Etapas de Ensino'

    def __str__(self):
        return self.nome


class Serie(models.Model):
    nome = models.CharField(verbose_name='Nome')
    etapa = models.ForeignKey(EtapaEnsino, verbose_name='Etapa')

    class Meta:
        verbose_name = 'Série'
        verbose_name_plural = 'Séries'

    def __str__(self):
        return '{} ({})'.format(self.nome, self.etapa)

    def has_permission(self, user):
        return user.roles.contains('Administrador')


class Disciplina(models.Model):
    nome = models.CharField(verbose_name='Nome')

    class Meta:
        icon = 'book-half'
        verbose_name = 'Disciplina'
        verbose_name_plural = 'Disciplinas'

    def __str__(self):
        return self.nome

    def has_permission(self, user):
        return user.roles.contains('Administrador')

    def get_dados_gerais(self):
        return self.values('nome')

    def get_topicos(self):
        return self.topico_set.ignore('disciplina').global_actions('AdicionarTopico')

    def view(self):
        return self.values('get_dados_gerais', 'get_topicos')


class Topico(models.Model):
    disciplina = models.ForeignKey(Disciplina, verbose_name='Disciplina')
    nome = models.CharField(verbose_name='Nome')

    class Meta:
        verbose_name = 'Tópico'
        verbose_name_plural = 'Tópicos'

    def __str__(self):
        return self.nome


class EscolaManager(models.Manager):
    def all(self):
        return self


class Escola(models.Model):

    nome = models.CharField(verbose_name='Nome')

    objects = models.Manager()

    class Meta:
        icon = 'building'
        verbose_name = 'Escola'
        verbose_name_plural = 'Escolas'

    def __str__(self):
        return self.nome

    def get_dados_gerais(self):
        return self.values('nome')

    def get_coordenadores(self):
        return self.coordenador_set.ignore('escola').global_actions('AdicionarCoordenador')

    def view(self):
        return self.values('get_dados_gerais', 'get_coordenadores')

    def has_permission(self, user):
        return user.roles.contains('Administrador')


@role('Coordenador', 'email', escola='escola')
class Coordenador(Pessoa):
    escola = models.ForeignKey(Escola, verbose_name='Escola')

    class Meta:
        verbose_name = 'Coordenador'
        verbose_name_plural = 'Coordenadores'


class AlunoManager(models.Manager):

    def all(self):
        return self.role_lookups(
            'Administrador'
        ).role_lookups(
            'Coordenador', escola='escola'
        ).dynamic_filters('escola').cards()


@role('Aluno', 'email', escola='escola')
class Aluno(Pessoa):
    escola = models.ForeignKey(Escola, verbose_name='Escola')
    foto = models.ImageField(verbose_name='Foto', upload_to='alunos', null=True, blank=True)

    objects = AlunoManager()

    class Meta:
        icon = 'person'
        verbose_name = 'Aluno'
        verbose_name_plural = 'Alunos'

    def has_permission(self, user):
        return user.roles.contains('Administrador', 'Coordenador')


class TurmaManager(models.Manager):

    def all(self):
        return self.role_lookups(
            'Administrador'
        ).role_lookups(
            'Coordenador', escola='escola'
        ).dynamic_filters('escola')


class Turma(models.Model):
    escola = models.ForeignKey(Escola, verbose_name='Escola')
    nome = models.CharField(verbose_name='Nome')
    serie = models.ForeignKey(Serie)
    alunos = models.ManyToManyField(Aluno, verbose_name='Alunos', blank=True)

    objects = TurmaManager()

    class Meta:
        icon = 'people'
        verbose_name = 'Turma'
        verbose_name_plural = 'Turmas'

    def __str__(self):
        return self.nome

    def has_permission(self, user):
        return user.roles.contains('Administrador', 'Coordenador')

class PerguntaManager(models.Manager):
    def all(self):
        return self.display('enunciado', 'get_resposta').rows()


class Pergunta(models.Model):
    enunciado = models.TextField(verbose_name='Enunciado')
    imagem = models.ImageField(verbose_name='Imagem', upload_to='perguntas', null=True, blank=True)

    alternativa_a = models.CharField(verbose_name='a)')
    alternativa_b = models.CharField(verbose_name='b)')
    alternativa_c = models.CharField(verbose_name='c)')
    alternativa_d = models.CharField(verbose_name='d)')

    resposta = models.CharField(verbose_name='Resposta', choices=[[i, i] for i in 'ABCD'])
    justificativa = models.TextField(verbose_name='Justificativa', null=True, blank=True)

    objects = PerguntaManager()

    class Meta:
        icon  = 'question-square'
        verbose_name = 'Pergunta'
        verbose_name_plural = 'Perguntas'
        fieldsets = {
            'Dados Gerais': ('enunciado', 'imagem'),
            'Alternativas': ('alternativa_a', 'alternativa_b', 'alternativa_c', 'alternativa_d'),
            'Gabarito': ('resposta', 'justificativa'),
        }

    def get_resposta(self):
        return getattr(self, 'alternativa_{}'.format(self.resposta.lower()))

    def __str__(self):
        return 'Pergunta {})'.format(self.id)


class AgendamentoManager(models.Manager):
    def all(self):
        return self.display('id', 'data')


class Agendamento(models.Model):
    data = models.DateField(verbose_name='Data')
    perguntas = models.ManyToManyField(Pergunta, verbose_name='Perguntas')
    alunos = models.ManyToManyField(Aluno, verbose_name='Alunos')

    objects = AgendamentoManager()

    class Meta:
        icon = 'clock-history'
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'

    def __str__(self):
        return 'Agendamento {}'.format(self.pk)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for aluno in self.alunos.all():
            simulado = Simulado.objects.filter(agendamento=self, aluno=aluno).first()
            if simulado is None:
                simulado = Simulado.objects.create(agendamento=self, aluno=aluno)
            for pergunta in self.perguntas.all():
                if not Resposta.objects.filter(simulado=simulado, pergunta=pergunta).exists():
                    Resposta.objects.create(simulado=simulado, pergunta=pergunta)

    def get_dados_gerais(self):
        return self.values('data')

    def get_perguntas(self):
        return self.perguntas.display('enunciado', 'get_resposta')

    def get_alunos(self):
        return self.alunos.cards()

    def view(self):
        return self.values('get_dados_gerais', 'get_perguntas', 'get_alunos')


class SimuladoManager(models.Manager):
    def all(self):
        return self.display('id', 'aluno', 'progresso')


class Simulado(models.Model):
    agendamento = models.ForeignKey(Agendamento, verbose_name='Agendamento')
    aluno = models.ForeignKey(Aluno, verbose_name='Aluno')
    progresso = models.IntegerField(verbose_name='Progresso', default=0)

    objects = SimuladoManager()

    class Meta:
        icon = 'list-ul'
        verbose_name = 'Simulado'
        verbose_name_plural = 'Simulado'

    def __str__(self):
        return 'Simulado {}'.format(self.pk)

    def get_dados_gerais(self):
        return self.values(('aluno', 'progresso'))

    def get_perguntas(self):
        return self.resposta_set.display('get_alternativas').rows().actions('RespostaA')

    def view(self):
        return self.values('get_dados_gerais', 'get_perguntas')


class Resposta(models.Model):
    simulado = models.ForeignKey(Simulado, verbose_name='Simulado')
    pergunta = models.ForeignKey(Pergunta, verbose_name='Pergunta', related_name='respostas_alunos')
    resposta = models.CharField(verbose_name='Resposta', null=True)
    correta = models.BooleanField(verbose_name='Correta', null=True)

    class Meta:
        verbose_name = 'Resposta'
        verbose_name_plural = 'Respostas'

    def get_alternativas(self):
        return 'a){}\nb){}'.format(
            self.pergunta.alternativa_a,
            self.pergunta.alternativa_b
        )

    def __str__(self):
        return '{}'.format(self.pergunta.enunciado)

    def has_permission(self, user):
        return False

    def has_view_permission(self, user):
        return False
