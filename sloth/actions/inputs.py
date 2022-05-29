from django.forms import widgets
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from sloth.utils import colors


class ColorInput(widgets.TextInput):

    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'd-none'
        html = super(ColorInput, self).render(name, value, attrs)
        cpid = '{}ColorPickSelector'.format(name)
        extra = '''
            <div id="{}ColorPickSelector" style="cursor:pointer;width:20px;height:20px;border:solid 1px #EEE;border-radius:5px"></div>
            <script>
            $(function(){{
            $("#{}ColorPickSelector").colorPick({{
                'initialColor' : '{}',
                'onColorSelected': function() {{
                     $("#id_{}").val(this.color);
                    this.element.css({{'backgroundColor': this.color, 'color': this.color}});
                }},
                'palette': {}
            }});
            }});
            </script>
            <style>#colorPick{{z-index:99999;}}</style>
        '''.format(cpid, cpid, value or '#FFFFFF', name, colors())
        return mark_safe('{}\n{}'.format(html, extra))


class PickInputMixin():
    def __init__(self, queryset, template_name='app/inputs/picker.html', multiple=False, grouper=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = queryset
        self.template_name = template_name
        self.multiple = multiple
        self.grouper = grouper

    def value_from_datadict(self, data, files, name):
        if self.allow_multiple_selected:
            getter = data.getlist
        else:
            getter = data.get
        return getter(name)

    def render(self, name, value, attrs=None, renderer=None, choices=()):
        grouped_objects = []
        values = value and (type(value) == int and [value] or [int(v) for v in value]) or []
        if self.grouper:
            groupers = self.queryset.values_list(self.grouper, flat=True).order_by(self.grouper).distinct()
        else:
            groupers = [None]
        for grouper in groupers:
            if grouper:
                grouped_qs = self.queryset.filter(**{self.grouper : grouper})
            else:
                grouped_qs = self.queryset
            grouped_objects.append((grouper, grouped_qs))
        return mark_safe(
            render_to_string(
                self.template_name, dict(
                    grouped_objects=grouped_objects, values=values, name=name, multiple=self.multiple
                )
            )
        )

class PickInput(PickInputMixin, widgets.Select):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class MultiplePickInput(PickInputMixin, widgets.SelectMultiple):
    def __init__(self, *args, **kwargs):
        kwargs.update(multiple=True)
        super().__init__(*args, **kwargs)


class QrCodeInput(widgets.TextInput):

    def render(self, name, value, attrs=None, **kwargs):
        widget = super().render(name, value, attrs=attrs, **kwargs)
        output = render_to_string('app/inputs/qrcode.html', dict(widget=widget, name=name))
        return mark_safe(output)
