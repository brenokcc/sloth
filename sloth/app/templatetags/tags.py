# -*- coding: utf-8 -*-
import locale
import datetime
import unicodedata
from django.template import Library
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from sloth.utils.formatter import format_value
from sloth.utils import colors, to_snake_case
from sloth.actions import ACTIONS


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
        if isinstance(v, dict) and not is_valueset(v):
            if is_image(v['value']):
                return k
    return None


@register.filter
def is_valueset(value):
    return type(value).__name__ == 'ValueSet'


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
    return user.is_superuser or obj.has_view_permission(user) or obj.has_permission(user)


@register.filter
def group_by_icon(actions):
    groups = dict(with_icon=[], without_icon=[])
    for action in actions:
        if action['icon']:
            groups['with_icon'].append(action)
        else:
            groups['without_icon'].append(action)
    return groups


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter('getattr')
def getattr2(obj, name):
    return getattr(obj, name)


@register.filter
def unaccented(s):
    nfkd_form = unicodedata.normalize('NFKD', s)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])


@register.filter
def true(value):
    return value in ('Sim', 'Yes', 'True', True)


@register.filter
def split(value):
    return value.split('\n')


@register.filter
def tabsplit(value):
    return value.split('\t')


@register.filter
def icontag(value):
    if value:
        if value.startswith('fa-'):
            return mark_safe('<i class="fa-solid {}"></i>'.format(value))
        elif value.startswith('bi-'):
            return mark_safe('<i class="bi {}"></i>'.format(value))
        elif value.startswith('mi-'):
            suffix = ''
            if value.endswith('-outlined'):
                suffix = '-outlined'
            elif value.endswith('-round'):
                suffix = '-round'
            elif value.endswith('-sharp'):
                suffix = '-sharp'
            if suffix:
                icon = '-'.join(value.split('-')[1:-1])
            else:
                icon = '-'.join(value.split('-')[1:])
            return mark_safe('<span class="material-icons{}">{}</span>'.format(suffix, icon.replace('-', '_')))
        else:
            return mark_safe('<i class="bi bi-{}"></i>'.format(value))
    return ''


@register.filter
def calendar(value):
    html = []
    items = []
    legend = []
    months = []
    for i, item in enumerate(value):
        if len(item) == 2: #  description, date
            item = (item[0], item[1], item[1], colors(i))
        elif len(item) == 3:
            if isinstance(item[2], str): #  description, date, color
                item = (item[0], item[1], item[1], item[2])
            else: #  description, date, date
                item = (item[0], item[1], item[2], colors(i))
        first_day_of_month = datetime.date(item[1].year, item[1].month, 1)
        if first_day_of_month not in months:
            months.append(first_day_of_month)
        first_day_of_month = datetime.date(item[2].year, item[2].month, 1)
        if first_day_of_month not in months:
            months.append(first_day_of_month)
        legend.append((item[3], item[0]))
        items.append(item)

    def color(day):
        for item in items:
            if day >= item[1] and day <= item[2]:
                return item[3]

    def month(first_day_of_month):
        days = {}
        first_day_of_calendar = first_day_of_month - datetime.timedelta(days=first_day_of_month.weekday())
        for i in range(0, (first_day_of_month - first_day_of_calendar).days):
            day = first_day_of_calendar + datetime.timedelta(days=i)
            days[day] = color(day)
        last_day_of_month = first_day_of_month + datetime.timedelta(days=0)
        while first_day_of_month.month == last_day_of_month.month:
            days[last_day_of_month] = color(last_day_of_month)
            last_day_of_month += datetime.timedelta(days=1)
        last_day_of_month += datetime.timedelta(days=-1)
        last_day_of_calendar = last_day_of_month + datetime.timedelta(days=0)
        while last_day_of_calendar.weekday() < 6:
            last_day_of_calendar += datetime.timedelta(days=1)
            days[last_day_of_calendar] = color(last_day_of_calendar)
        context = dict(days=days, start=first_day_of_month, today=datetime.date.today())
        return render_to_string('renderers/calendar/calendar.html', context=context)

    for first_day_of_month in months:
        html.append(month(first_day_of_month))
    html.append(render_to_string('renderers/calendar/legend.html', dict(legend=legend)))

    return mark_safe(''.join(html))

@register.filter
def action_link(action_name):
    cls = ACTIONS[action_name]
    metadata = cls.get_metadata()
    return mark_safe('<a href="/app/action/{}/" class="{}">{}</a>'.format(
        to_snake_case(action_name), 'popup' if metadata['modal'] else '', metadata['name']
    ))