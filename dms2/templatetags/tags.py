# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

from django.db.models.fields.files import FieldFile
from django.template import Library
from django.utils.safestring import mark_safe

register = Library()


@register.filter('format')
def _format(obj):
    if obj is not None:
        if isinstance(obj, str):
            return obj
        elif isinstance(obj, bool):
            return 'Sim' if obj else 'Não'
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%d/%m/%Y %H:%M')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%d/%m/%Y')
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, list):
            return '<ul>{}</ul>'.format('<li>{}</li>'.join([str(o) for o in obj]))
        elif hasattr(obj, 'all'):
            return '<ul>{}</ul>'.format('<li>{}</li>'.join([str(o) for o in obj]))
        elif isinstance(obj, dict):
            return mark_safe(
                '<br>'.join(['<b>{}</b>: {}'.format(k, v) for k, v in obj.items()])
            )
        elif isinstance(obj, FieldFile):
            return obj.url
        return str(obj)
    return ''


@register.filter
def index(indexable, i):
    return indexable[i]


@register.filter
def is_image(value):
    if isinstance(value, str):
        if value.startswith('/media') or value.startswith('/static'):
            for extension in ('.jpg', '.png'):
                if value.endswith(extension):
                    return True
    return False


@register.filter
def format_image(value):
    return mark_safe(
        '<div class="photo-circle"><img src={}/></div>'.format(value)
    )

