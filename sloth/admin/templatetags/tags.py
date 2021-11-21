# -*- coding: utf-8 -*-

from django.template import Library
from django.utils.safestring import mark_safe

from sloth.utils.formatter import format_value

register = Library()


@register.filter('format')
def _format(value):
    return format_value(value)


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
    return text and text.isupper()


@register.filter
def is_one_to_one_field_controller(name):
    return name and name.isupper() and name.count('--') == 0


@register.filter
def is_one_to_many_field_controller(name):
    return name and name.isupper() and name.count('--') == 1


@register.filter
def is_controller_field(name):
    return is_one_to_one_field_controller(name) or is_one_to_many_field_controller(name)


@register.filter
def image_src(path):
    if path:
        path = str(path)
        if path.startswith('/') or path.startswith('http'):
            return path
        return '/media/{}'.format(path)
    return '/static/images/no-image.png'


@register.filter
def image_key(dictionary):
    for k, v in dictionary.items():
        if v and isinstance(v, str) and v.split('.')[-1].lower() in ('png', 'jpg', 'jpeg'):
            return k
    return None


@register.filter
def column_chart_height(percentage):
    return 3*int(percentage)


@register.filter
def column_chart_serie_width(data):
    for series in data['series'].values():
        return 40 * len(series)


@register.filter
def column_chart_series_width(data):
    width = 0
    for series in data['series'].values():
        for _ in series:
            width += 40
    return width


@register.filter
def column_chart_width(data):
    return column_chart_series_width(data) + 50


@register.filter
def multiply(value, n):
    return int(value * n)


@register.filter
def divide(value, n):
    return int(value / n)


@register.filter
def add(value, n):
    return int(value + n)


@register.filter
def can_view(obj, user):
    return obj.can_view(user)

