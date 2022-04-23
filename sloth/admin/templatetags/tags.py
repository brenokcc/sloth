# -*- coding: utf-8 -*-

from django.template import Library
from django.utils.safestring import mark_safe

from sloth.utils.formatter import format_value

register = Library()


@register.filter
def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


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
        print(k, v)
        if is_image(v):
            return k
    return None


@register.filter
def is_image(value):
    return str(value).split('.')[-1].lower() in ('png', 'jpg', 'jpeg')


@register.filter
def column_chart_height(percentage):
    return 3*int(percentage)


@register.filter
def column_chart_serie_width(data):
    for series in data.values():
        return 100 * len(series)


@register.filter
def column_chart_series_width(data):
    width = 0
    for series in data.values():
        for _ in series:
            width += 100
    return width


@register.filter
def column_chart_width(data):
    return column_chart_series_width(data) + 100


@register.filter
def multiply(value, n):
    return value * n


@register.filter
def add(value, n):
    return value + n


@register.filter
def has_view_permission(obj, user):
    return obj.has_view_permission(user)

