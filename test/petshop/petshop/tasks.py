import time
from sloth.api.tasks import Task


class Tarefa(Task):
    def run(self):
        for i in self.iterate(range(0, 20)):
            time.sleep(1)
            if i % 5 == 0:
                self.message('Executando passo {}'.format(i))
        self.finalize()
