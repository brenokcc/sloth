from sloth.app.dashboard import Dashboard
from .models import Disciplina, Escola, Turma, Aluno, Pergunta, Agendamento, Simulado

class SimuladoDashboard(Dashboard):

    def load(self, request):
        self.shortcuts(Disciplina, Escola, Turma, Aluno, Pergunta, Agendamento, Simulado)
