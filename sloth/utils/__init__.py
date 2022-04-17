# -*- coding: utf-8 -*-

import datetime
import re
from decimal import Decimal
from django.apps import apps
from django.db.models.fields.files import FieldFile


def getattrr(obj, args):
    if args == '__str__':
        attrs = [args]
    else:
        attrs = args.split('__')
    return _getattr_rec(obj, attrs)


def _getattr_rec(obj, attrs):
    attr_name = attrs.pop(0)
    if obj is not None:
        attr = getattr(obj, attr_name)
        if hasattr(attr, 'all'):
            value = attr.all()
        elif callable(attr):
            value = attr()
        else:
            value = attr
        if attrs:
            return _getattr_rec(value, attrs)
        else:
            return attr, value
    return None, None


def igetattr(obj, attr):
    for a in dir(obj):
        if a.lower() == attr.lower():
            return getattr(obj, a)


def serialize(obj):
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
        elif isinstance(obj, bool):
            return obj
        elif isinstance(obj, list):
            return [str(o) for o in obj]
        elif hasattr(obj, 'all'):
            return [str(o) for o in obj.filter()]
        elif isinstance(obj, FieldFile):
            return obj and obj.url or '/static/images/no-image.png'
        return str(obj)
    return None


def pretty(name):
    if name.startswith('get_'):
        name = name[4:].replace('_', ' ')
    name = name.replace('_', ' ')
    if name.islower():
        regex_roman_numbers = r'^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$'
        name = re.sub(r'\.', '. ', name or '')  # adding spaces to short names
        name = re.sub(r'\s+', ' ', name)  # removing multiple spaces
        name = name.title()  # camel case
        tokens = name.split(' ')  # splitting into a list
        ignore = [
            'de', 'di', 'do', 'da', 'dos', 'das', 'dello', 'della', 'dalla', 'dal',
            'del', 'e', 'em', 'na', 'no', 'nas', 'nos', 'van', 'von', 'y', 'a', 'por', 'para'
        ]
        output = []
        for token in tokens:
            if token.lower() in ignore:
                output.append(token.lower())
            elif re.match(regex_roman_numbers, token.upper()):
                output.append(token.upper())
            else:
                output.append(token)
        name = ' '.join(output)
    return name


def load_menu(user):
    from .. import PROXIED_MODELS
    items = []
    if user:
        for model in apps.get_models():
            if model not in PROXIED_MODELS:
                app_label = model.metaclass().app_label
                model_name = model.metaclass().model_name
                model_verbose_name_plural = model.metaclass().verbose_name_plural
                icon = getattr(model.metaclass(), 'icon', None)
                url = '/adm/{}/{}/'.format(app_label, model_name)
                item = dict(label=pretty(str(model_verbose_name_plural)), description=None, url=url, icon=icon, subitems=[])
                if model().has_list_permission(user):
                    items.append(item)
    return items




