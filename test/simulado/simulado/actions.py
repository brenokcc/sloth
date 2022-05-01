from sloth import actions
from .models import Topico, Coordenador, Turma, Escola, Aluno


class AdicionarTopico(actions.Action):

    class Meta:
        model = Topico
        fields = 'nome',
        related_field = 'disciplina'
        has_permission = 'Administrador',


class AdicionarCoordenador(actions.Action):

    class Meta:
        model = Coordenador
        fields = 'nome', 'email'
        related_field = 'escola'
        has_permission = 'Administrador',


class AddTurma(actions.Action):
    escola = actions.ModelChoiceField(queryset=Escola.objects.role_lookups('Administrador').role_lookups('Coordenador', id='escola'), label='Escola')

    class Meta:
        model = Turma
        has_permission = 'Administrador', 'Coordenador'


class AddAluno(actions.Action):
    escola = actions.ModelChoiceField(queryset=Escola.objects.role_lookups('Administrador').role_lookups('Coordenador', id='escola'), label='Escola')

    class Meta:
        model = Aluno
        has_permission = 'Administrador', 'Coordenador'


class RespostaA(actions.Action):

    class Meta:
        style = 'success'
        verbose_name = 'Resposta A)'
        confirmation = True

