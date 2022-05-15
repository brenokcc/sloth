from django.forms import widgets
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
