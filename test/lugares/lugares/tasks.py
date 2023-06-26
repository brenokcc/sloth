import time
from sloth.api.tasks import Task

class Contar(Task):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        for i in self.iterate(list(range(1, 20))):
            time.sleep(0.5)
            self.message(f'Executando passo {i}')
        self.finalize()

    def has_permission(self, user):
        return True