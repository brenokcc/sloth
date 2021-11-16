# -*- coding: utf-8 -*-
import json
from uuid import uuid1

from django.template.loader import render_to_string

from .query import QuerySet
from .statistics import QuerySetStatistics
from . import formatters
from .utils import getattrr, serialize, pretty


class ValueSet(dict):
    def __init__(self, instance, names, image=None):
        self.instance = instance
        self.metadata = dict(
            model=type(instance), names={}, metadata=[], actions=[], type='fieldset', attr=None,
            attach=[], append=[], image=image, template=None, request=None, primitive=False
        )
        for attr_name in names:
            if isinstance(attr_name, tuple):
                for name in attr_name:
                    self.metadata['names'][name] = 100 // len(attr_name)
            else:
                self.metadata['names'][attr_name] = 100
        super().__init__()

    def actions(self, *names):
        self.metadata['actions'] = list(names)
        return self

    def append(self, *names):
        self.metadata['append'] = list(names)
        return self

    def attach(self, *names):
        self.metadata['attach'] = list(names)
        return self

    def image(self, image):
        self.metadata['image'] = image
        return self

    def template(self, name):
        self.metadata['template'] = name
        return self

    def attr(self, name):
        self.metadata['attr'] = name
        return self

    def contextualize(self, request):
        self.metadata.update(request=request)
        return self

    def debug(self):
        print(json.dumps(self.serialize(wrap=True, verbose=True), indent=4, ensure_ascii=False))

    def load(self, wrap=False, verbose=False, formatted=False, valueset=None, size=True):
        if self.metadata['names']:
            for attr_name, width in self.metadata['names'].items():
                if self.metadata['request'] is None or self.instance.check_attr_access(attr_name, self.metadata['request'].user):
                    attr, value = getattrr(self.instance, attr_name)
                    path = '/{}/{}/{}/{}/'.format(self.instance.metaclass().app_label, self.instance.metaclass().model_name, self.instance.pk, attr_name)
                    if isinstance(value, QuerySet):
                        if valueset is not None:
                            valueset.metadata['type'] = 'fieldsets'
                        value.contextualize(self.metadata['request'])
                        verbose_name = getattr(attr, 'verbose_name', attr_name) if verbose else attr_name
                        if wrap:
                            value = value.serialize(path=path, wrap=wrap, verbose=verbose, formatted=formatted)
                            value['name'] = verbose_name
                        else:
                            value = [str(o) for o in value]
                    elif isinstance(value, QuerySetStatistics):
                        if valueset is not None:
                            valueset.metadata['type'] = 'fieldsets'
                        value.contextualize(self.metadata['request'])
                        verbose_name = getattr(attr, 'verbose_name', attr_name) if verbose else attr_name
                        value = value.serialize(path=path, wrap=wrap)
                        if wrap:
                            value['name'] = verbose_name
                    elif isinstance(value, ValueSet):
                        if valueset is not None:
                            valueset.metadata['type'] = 'fieldsets'
                        value.contextualize(self.metadata['request'])
                        actions = getattr(value, 'metadata')['actions']
                        image_attr_name = getattr(value, 'metadata')['image']
                        template = getattr(value, 'metadata')['template']
                        verbose_name = getattr(attr, 'verbose_name', attr_name) if verbose else attr_name
                        key = attr_name
                        value.load(wrap=wrap, verbose=verbose, formatted=formatted, valueset=self, size=size)
                        value = dict(uuid=uuid1().hex, type=self.metadata['type'], name=verbose_name, key=key,
                                     actions=[], data=value, path=path) if wrap else value
                        if wrap:
                            for form_name in actions:
                                form_cls = self.instance.action_form_cls(form_name)
                                if self.metadata['request'] is None or form_cls.check_permission(
                                        request=self.metadata['request'], instantiator=self.instance,
                                ):
                                    action = form_cls.get_metadata(path)
                                    value['actions'].append(action)
                            value['path'] = path
                            if image_attr_name:
                                image_attr = getattr(self.instance, image_attr_name)
                                image = image_attr() if callable(image_attr) else image_attr
                                if image:
                                    image = str(image)
                                    if not image.startswith('/') and not image.startswith('http'):
                                        image = '/media/{}'.format(image)
                                    value['image'] = image
                            if template:
                                value['template'] = '{}.html'.format(template)
                    else:
                        self.metadata['primitive'] = True
                        if formatted and getattr(attr, 'template', None):
                            template = attr.template
                            template = template if template.endswith('.html') else '{}.html'.format(template)
                            value = render_to_string(
                                template, dict(value=value, instance=self.instance)
                            )
                        else:
                            value = serialize(value)
                        if formatted and value in (None, ''):
                            value = '-'
                        if size:
                            value = dict(value=value, width=width)

                    if verbose:
                        attr_name = pretty(self.metadata['model'].get_attr_verbose_name(attr_name)[0])

                    self[attr_name] = value
        else:
            self['id'] = self.instance.id
            self[self.metadata['model'].__name__.lower()] = str(self.instance)

        return self

    def __str__(self):
        return json.dumps(self, indent=4, ensure_ascii=False)

    def serialize(self, wrap=False, verbose=False, formatted=False):
        self.load(wrap=wrap, verbose=verbose, formatted=formatted)
        if wrap:
            data = {}
            if self.metadata['primitive']:
                data['Dados Gerais'] = dict(
                    uuid=uuid1().hex, type='fieldset', name='Dados Gerais', key='default', actions=[], data=self,
                    path=None
                )
            else:
                data.update(self)
            icon = getattr(self.instance.metaclass().app_label, 'icon', None)
            output = dict(
                uuid=uuid1().hex, type='object', name=str(self.instance),
                icon=icon, data=data, actions=[], attach=[], append={}
            )
            for form_name in self.metadata['actions']:
                path = '/{}/{}/{}/'.format(
                    self.instance.metaclass().app_label,
                    self.instance.metaclass().model_name, self.instance.pk
                )
                action = self.instance.action_form_cls(form_name).get_metadata(path)
                output['actions'].append(action)
            for attr_name in self.metadata['attach']:
                name = getattr(getattr(self.instance, attr_name), 'verbose_name', attr_name)
                path = '/{}/{}/{}/{}/'.format(
                    self.instance.metaclass().app_label,
                    self.instance.metaclass().model_name,
                    self.instance.pk, attr_name
                )
                output['attach'].append(dict(name=name, path=path))
            for attr_name in self.metadata['append']:
                output['append'].update(
                    self.instance.values(attr_name).contextualize(self.metadata['request']).load(
                        wrap=wrap, verbose=verbose, formatted=formatted
                    )
                )
            return output
        else:
            if len(self.metadata['names']) == 1:
                return self[list(self.metadata['names'].keys())[0]]
            return self

    def html(self, uuid=None):
        serialized = self.serialize(wrap=True, verbose=True, formatted=True)
        icon = serialized['icon']
        name = serialized['name']
        data = serialized['data']
        actions = serialized['actions']
        attach = serialized['attach']
        append = serialized['append']
        if uuid:
            data['uuid'] = uuid
            name = None
        return render_to_string(
            'adm/valueset.html',
            dict(uuid=uuid, icon=icon, name=name, data=data, actions=actions, attach=attach, append=append),
            request=self.metadata['request']
        )
