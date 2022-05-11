
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
        previous_progress = 0
        for obj in iterable:
            if self.task_id in TaskModel.STOPPED_TASKS:
                break
            self.partial += 1
            progress = 100 if self.total == 0 else int(self.partial/self.total*100)
            if (progress - previous_progress) > 5 or progress == 100:
                previous_progress = progress
                TaskModel.objects.filter(pk=self.task_id).update(progress=progress)
            yield obj

    def finalize(self, message):
        TaskModel.objects.filter(pk=self.task_id).update(message=message, end=datetime.datetime.now())
