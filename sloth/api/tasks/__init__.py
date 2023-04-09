import traceback
import datetime
from threading import Thread
from django.core.cache import cache
from sloth.api.models import Task as TaskModel


class Task(Thread):

    def __init__(self, *args, **kwargs):
        self.total = 0
        self.partial = 0
        self.previous = 0
        self.task_id = None
        super().__init__(*args, **kwargs)

    def start(self, request):
        task = TaskModel.objects.create(name=self.get_name(), user=request.user)
        self.task_id = task.id
        super().start()

    def get_name(self):
        cls = type(self)
        if hasattr(cls, 'Meta'):
            return getattr(cls, 'Meta').verbose_name
        return cls.__name__

    def get_update_progress_interval(self):
        return 5

    def running(self):
        if cache.get('task_{}_stopped'.format(self.task_id)) is None:
            if self.partial == 0:
                TaskModel.objects.filter(pk=self.task_id).update(total=self.total)
            self.partial += 1
            progress = 100 if self.total == 0 else int(self.partial / self.total * 100)
            if (self.previous == 0 and progress) or (progress - self.previous) >= self.get_update_progress_interval() or self.partial % 1000 == 0 or progress == 100:
                self.previous = progress
                TaskModel.objects.filter(pk=self.task_id).update(progress=progress, partial=self.partial)
            return True
        return False

    def iterate(self, iterable):
        if hasattr(iterable, 'model') and hasattr(iterable, 'count'):
            self.total = iterable.count()
        else:
            self.total = len(iterable)
        for obj in iterable:
            if self.running():
                yield obj
            else:
                break

    def message(self, text):
        TaskModel.objects.filter(pk=self.task_id).update(message=text)

    def finalize(self, text='Ação realizada com sucesso'):
        TaskModel.objects.filter(pk=self.task_id).update(message=text, end=datetime.datetime.now(), partial=self.partial)

    def error(self, text, exception=None):
        if exception:
            traceback.print_exc()
        TaskModel.objects.filter(pk=self.task_id).update(error=text, end=datetime.datetime.now(), partial=self.partial)
