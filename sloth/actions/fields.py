from django.forms import fields
from . import inputs

class QrCodeField(fields.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(widget=inputs.QrCodeInput())
        super().__init__(*args, **kwargs)
