import traceback
import datetime
from threading import Thread

from ..api.models import Task as TaskModel


class Task(Thread):

    def __init__(self, *args, **kwargs):
        self.total = 0
        self.partial = 0
        self.task_id = None
        super().__init__(*args, **kwargs)

    def start(self, request):
        task = TaskModel.objects.create(name=type(self).__name__, user=request.user)
        self.task_id = task.id
        super().start()

    def iterate(self, iterable):
        self.total = len(iterable)
        previous = 0
        for obj in iterable:
            if self.task_id in TaskModel.STOPPED_TASKS:
                break
            self.partial += 1
            progress = 100 if self.total in (0, 100) else int(self.partial/self.total*100)
            if (previous == 0 and progress) or (progress - previous) > 5 or self.partial % 1000 == 0 or progress == 100:
                previous = progress
                TaskModel.objects.filter(pk=self.task_id).update(progress=progress)
            yield obj

    def finalize(self, text):
        TaskModel.objects.filter(pk=self.task_id).update(message=text, end=datetime.datetime.now())

    def error(self, text, exception=None):
        if exception:
            traceback.print_exc()
        TaskModel.objects.filter(pk=self.task_id).update(error=text, end=datetime.datetime.now())
