# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

from django.conf import settings
from django.utils.safestring import mark_safe
from django.db.models.fields.files import FieldFile


def format_value(obj):
    if obj not in (None, ''):
        if isinstance(obj, str):
            if obj[0] == '#' and len(obj) == 7:
                style = 'float:left;width:20px;height: 20px; margin-right:5px;border-radius:5px'
                return mark_safe('<div style="background-color:{};{}"></div>'.format(obj, style))
            return obj
        elif isinstance(obj, bool):
            return 'Sim' if obj else 'Não'
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%d/%m/%Y %H:%M')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%d/%m/%Y')
        elif isinstance(obj, float):
            return format_decimal(obj)
        elif isinstance(obj, Decimal):
            return format_decimal(obj)
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
                '<dl>{}</dl>'.format(''.join(['<dt>{}</dt><dd>{}</dd>'.format(k, format_value(v)) for k, v in obj.items()]))
            )
        elif isinstance(obj, FieldFile):
            return obj.url
        return str(obj)
    return '-'


def format_decimal(value, decimal_places=2):
    str_format = '{{:,.{}f}}'.format(decimal_places)
    if value is not None:
        value = str_format.format(Decimal(value))
        if settings.LANGUAGE_CODE == 'pt-br':
            value = value.replace(',', '#').replace('.', ',').replace('#', '.')
    return value


def format_decimal3(value):
    if value is None:
        return ''
    return format_decimal(value, 3)


def format_decimal1(value):
    if value is None:
        return ''
    return format_decimal(value, 1)