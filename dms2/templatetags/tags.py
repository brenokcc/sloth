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
            return mark_safe(
                '<ul>{}</ul>'.format(''.join(['<li>{}</li>'.format(o) for o in obj]))
            )
        elif hasattr(obj, 'all'):
            return mark_safe(
                '<ul>{}</ul>'.format(''.join(['<li>{}</li>'.format(o) for o in obj]))
            )
        elif isinstance(obj, dict):
            return mark_safe(
                '<dl>{}</dl>'.format(''.join(['<dt>{}</dt><dd>{}</dd>'.format(k, v) for k, v in obj.items()]))
            )
        elif isinstance(obj, FieldFile):
            return obj.url
        return str(obj)
    return ''


@register.filter
def index(indexable, i):
    return indexable[i]


@register.filter
def mobile(request):
    if request:
        width = int(request.COOKIES.get('width', 0))
        return width if width < 600 else False
    return False


@register.filter
def tablet(request):
    if request:
        width = int(request.COOKIES.get('width', 0))
        return width if 600 < width < 800 else False
    return False


@register.filter
def formfield(form, name):
    return form[name]


@register.filter
def label_tag(html):
    return mark_safe(html.replace(':', ''))


@register.filter
def isupper(text):
    return text.isupper()


@register.filter
def is_one_to_one_field_controller(name):
    return name.isupper() and name.count('--') == 0


@register.filter
def is_one_to_many_field_controller(name):
    return name.isupper() and name.count('--') == 1


@register.filter
def is_controller_field(name):
    return is_one_to_one_field_controller(name) or is_one_to_many_field_controller(name)
