import time
from sloth.api.tasks import Task

class TarefaAssincrona(Task):
    def run(self):
        for i in self.iterate(range(1, 10)):
            time.sleep(1)
        self.finalize('Tarefa concluída com sucesso!')
