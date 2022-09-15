from django.forms import *
from . import inputs

class QrCodeField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(widget=inputs.QrCodeInput())
        super().__init__(*args, **kwargs)


class ModelChoiceField(ModelChoiceField):
    def __init__(self, *args, **kwargs):
        self.auto_user = kwargs.pop('auto_user', False)
        super().__init__(*args, **kwargs)


class TextField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(widget=Textarea())
        super().__init__(*args, **kwargs)


class CurrentUserField(ModelChoiceField):
    def __init__(self, **kwargs):
        from django.contrib.auth.models import User
        super().__init__(User.objects, **kwargs)
