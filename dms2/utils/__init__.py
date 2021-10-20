# -*- coding: utf-8 -*-

import datetime
from decimal import Decimal

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
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


def get_field(cls, lookup):
    model = cls
    attrs = lookup.split('__')
    while attrs:
        attr_name = attrs.pop(0)
        if attrs:  # go deeper
            field = getattr(model, '_meta').get_field(attr_name)
            model = field.related_model
        else:
            try:
                return getattr(model, '_meta').get_field(attr_name)
            except FieldDoesNotExist:
                pass
    return None


def to_verbose_name(cls, lookup):
    field = get_field(cls, lookup)
    if field:
        return str(field.verbose_name), True
    attr = getattr(cls, lookup)
    return getattr(attr, 'verbose_name', lookup), False


def to_display(cls, lookups, verbose=False):
    display = {}
    for lookup in lookups:
        verbose_name, sort = to_verbose_name(cls, lookup)
        display[verbose_name if verbose else lookup] = dict(key=lookup, name=verbose_name, sort=sort)
    return display


def to_filters(cls, lookups, verbose=False):
    filters = {}
    for lookup in lookups:
        field = get_field(cls, lookup)
        field_type_name = type(field).__name__
        filter_type = 'choices'
        if 'Boolean' in field_type_name:
            filter_type = 'boolean'
        elif 'DateTime' in field_type_name:
            filter_type = 'datetime'
        elif 'Date' in field_type_name:
            filter_type = 'date'
        filters[str(field.verbose_name) if verbose else lookup] = dict(key=lookup, name=field.verbose_name,
                                                                       type=filter_type)
    return filters


def to_ordering(cls, lookups, verbose=False):
    ordering = {}
    for lookup in lookups:
        field = get_field(cls, lookup)
        ordering[str(field.verbose_name) if verbose else lookup] = dict(key=lookup, name=field.verbose_name)
    return ordering

