# -*- coding: utf-8 -*-

import datetime
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
            return [str(o) for o in obj]
        elif isinstance(obj, FieldFile):
            return obj.url
        return str(obj)
    return None


def load_menu(user):
    items = []
    for model in apps.get_models():
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        model_verbose_name = model._meta.verbose_name
        model_verbose_name_plural = model._meta.verbose_name_plural
        icon = getattr(model._meta, 'icon', None)
        url = '/adm/{}/{}/'.format(app_label, model_name)
        item = dict(label=str(model_verbose_name_plural), description=None, url=url, icon=icon, subitems=[])
        for name, attr in model.objects._queryset_class.__dict__.items():
            if hasattr(attr, 'decorated'):
                attr_verbose_name = getattr(attr, 'verbose_name')
                attr_icon = getattr(attr, 'icon', None)
                attr_description = attr_verbose_name
                if name == 'all':
                    attr_url = url
                    attr_verbose_name = model_verbose_name_plural
                    item.update(label=model_verbose_name)
                else:
                    attr_url = '{}{}/'.format(url, name)
                subitem = dict(label=attr_verbose_name, icon=attr_icon, description=attr_description, url=attr_url)
                item['subitems'].append(subitem)
        items.append(item)
    return items




