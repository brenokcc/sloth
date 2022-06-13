from django.forms import *
from . import inputs

class QrCodeField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(widget=inputs.QrCodeInput())
        super().__init__(*args, **kwargs)


class ModelChoiceField(ModelChoiceField):
    def __init__(self, *args, **kwargs):
        if 'username_lookup' in kwargs:
            self.username_lookup = kwargs.pop('username_lookup')
        super().__init__(*args, **kwargs)
