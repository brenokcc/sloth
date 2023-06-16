# -*- coding: utf-8 -*-
import json
from uuid import uuid1
import pprint
from functools import lru_cache
from django.db.models import Model
from django.template.loader import render_to_string
from sloth.actions import Action
from sloth.api.templatetags.tags import is_ajax
from sloth.core.queryset import QuerySet
from sloth.core.statistics import QuerySetStatistics
from sloth.utils import getattrr, serialize, pretty, to_snake_case


def check_fieldsets_type(item):
    types = 'fieldset', 'fieldset-list', 'fieldset-group'
    for name, subitem in item.items():
        if 'type' in subitem and subitem['type'] in types:
            check_fieldsets_type(subitem['data'])
            subitem['type'] = check_fieldset_type(subitem)


def check_fieldset_type(item):
    if is_fieldset_group(item['data']):
        first = item['data'][next(iter(item['data']))]
        return 'fieldset-group'
    elif is_fieldset_list(item['data']):
        return 'fieldset-list'
    else:
        return 'fieldset'


def is_fieldset_list(item):
    types = 'fieldset', 'queryset', 'statistics'
    for name, subitem in item.items():
        if 'type' in subitem and subitem['type'] in types:
            return True
    return False


def is_fieldset_group(item):
    for name, subitem in item.items():
        if 'type' in subitem and subitem['type'] == 'fieldset-list':
            return True
    return False


class ValueSet(dict):
    def __init__(self, instance, names):
        self.path = None
        self.request = None
        self.instance = instance
        self.metadata = dict(
            model=type(instance), names={}, metadata=[], actions=[], type=None, attr=None, source=None,
            attach=[], append={}, image=None, template=None, primitive=False, verbose_name=None,
            title=None, subtitle=None, status=None, icon=None, only=[], refresh={}, inline_actions=[],
            cards=[], shortcuts=[], collapsed=False, printing=False
        )
        for attr_name in names:
            if isinstance(attr_name, tuple):
                for name in attr_name:
                    self.metadata['names'][name] = 100 // len(attr_name)
            else:
                self.metadata['names'][attr_name] = 100
        super().__init__()

    def collapsed(self, flag=True):
        self.metadata['collapsed'] = flag
        return self

    def expand(self):
        return self.collapsed(False)

    def actions(self, *names):
        self.metadata['actions'] = [to_snake_case(name) for name in names]
        return self

    def inline_actions(self, *names):
        self.metadata['inline_actions'] = [to_snake_case(name) for name in names]
        return self

    def append(self, *names, position='right'):
        self.metadata['append'][position] = [to_snake_case(name) for name in names]
        return self

    def top(self, *names):
        return self.append(*names, position='top')

    def left(self, *names):
        return self.append(*names, position='left')

    def right(self, *names):
        return self.append(*names, position='right')

    def bottom(self, *names):
        return self.append(*names, position='bottom')

    def attach(self, *names):
        self.metadata['attach'] = [to_snake_case(name) for name in names]
        return self

    def image(self, image):
        image_attr = getattr(self.instance, image)
        self.metadata['image'] = (image_attr() if callable(image_attr) else image_attr) or '/static/images/no-image.png'
        return self

    def title(self, title):
        self.metadata['title'] = title
        return self

    def subtitle(self, subtitle):
        self.metadata['subtitle'] = subtitle
        return self

    def status(self, status):
        self.metadata['status'] = status
        return self

    def renderer(self, name):
        self.metadata['template'] = name
        return self

    def split(self, n=2):
        return self.renderer('valueset/{}-column'.format(n))

    def verbose_name(self, name):
        self.metadata['verbose_name'] = pretty(name)
        return self

    def attr(self, name, source=False):
        self.metadata['attr'] = name
        self.metadata['names'] = {name: 100}
        if source:
            return self.source(name)
        else:
            return self

    def get_allowed_attrs(self, recursive=True):
        allowed = []
        for key in ('actions', 'inline_actions', 'attach'):
            allowed.extend(self.metadata[key])
        for items in self.metadata['append']:
            allowed.extend(items)
        allowed.extend([name for name in self.metadata['names'].keys() if name.startswith('get_')])
        return allowed

    def source(self, name):
        self.metadata['source'] = name
        return self

    def reload(self, seconds=5, condition=None, max_requests=12):
        self.metadata['refresh'] = dict(seconds=seconds, condition=condition, retry=max_requests)
        return self

    def contextualize(self, request):
        if request:
            self.path = request.path
            self.request = request
        return self

    def debug(self):
        print(json.dumps(self.serialize(wrap=True), indent=4, ensure_ascii=False))

    def apply_role_lookups(self, user):
        return self

    def action_form_cls(self, action):
        return type(self.instance).action_form_cls(action)

    def has_permission(self, user):
        return user.is_superuser or self.instance.has_permission(user)

    def has_children(self):
        if type(self.instance):
            field_names = [field.name for field in self.instance.metaclass().fields]
            for name in self.metadata['names']:
                if name in field_names:
                    return False
            return True
        return False

    def refresh_data(self):
        refresh = self.metadata['refresh']
        if refresh:
            if refresh['condition']:
                deny = 'not ' in refresh['condition']
                satisfied = getattr(self.instance, refresh['condition'].replace('not ', ''))
                if callable(satisfied):
                    satisfied = satisfied()
                if deny and not satisfied or satisfied:  # condition was satisfied
                    return dict(seconds=refresh['seconds'], retry=refresh['retry'])
                else:
                    return dict(seconds=refresh['seconds'], retry=0)
            else:
                return dict(seconds=refresh['seconds'], retry=refresh['retry'])
        return {}

    def get_api_schema(self, recursive=False):
        schema = dict()
        for attr_name, width in self.metadata['names'].items():
            try:
                attr, value = getattrr(self.instance, attr_name)
            except BaseException as e:
                continue
            if isinstance(value, QuerySet):
                dict(type='array', items=dict(type='object', properties=schema))
            elif isinstance(value, QuerySetStatistics):
                pass
            elif isinstance(value, ValueSet):
                schema[attr_name] = dict(type='object', properties=value.get_api_schema(recursive=True))
            else:
                schema[attr_name] = self.instance.get_attr_api_type(attr_name)
        if recursive:
            return schema
        return dict(type='object', properties=schema)

    def load(self, wrap=True, detail=False, deep=0):
        if self.metadata['names']:
            is_app = self.request and self.request.path.startswith('/app/')
            for i, (attr_name, width) in enumerate(self.metadata['names'].items()):
                if self.request is None or self.instance.has_attr_permission(self.request.user, attr_name):
                    lazy = (wrap and (deep > 1 or (deep > 0 and i > 0)) and self.metadata['template'] is None) and not self.metadata['printing']
                    attr, value = getattrr(self.instance, attr_name)
                    path = self.path
                    if path and self.metadata['attr'] is None and attr_name != 'all':
                        tokens = path.split('?')
                        path = '{}{}/'.format(tokens[0], attr_name)
                        if len(tokens) == 2:
                            path = '{}?{}'.format(path, tokens[1])
                    if self.request and self.request.META.get('QUERY_STRING'):
                        path = '{}?{}'.format(path, self.request.META.get('QUERY_STRING').replace('?tab=1', ''))

                    assyncronous = getattr(attr, '__assyncronous__', None)
                    if assyncronous and not is_ajax(self.request):
                        data = dict(key=attr_name, type='assyncronous', path=path)
                    elif isinstance(value, QuerySet) or hasattr(value, '_queryset_class'):  # RelatedManager
                        qs = value if isinstance(value, QuerySet) else value.filter() # ManyRelatedManager
                        qs.instantiator = self.instance
                        qs.metadata['uuid'] = attr_name
                        qs.metadata['path'] = path
                        verbose_name = getattr(attr, '__verbose_name__', qs.metadata['verbose_name'])
                        if verbose_name is None:
                            verbose_name = pretty(attr_name)
                        qs.verbose_name(verbose_name)
                        template = getattr(attr, '__template__', None)
                        template = 'renderers/{}.html'.format(template) if template else None
                        if self.request:
                            source = None if self.request.path.startswith('/app/') else self.metadata['source']
                            qs = qs.contextualize(self.request, source).apply_role_lookups(self.request.user)
                        if wrap:
                            if template or (self.metadata['primitive'] and deep > 0):
                                data = dict(value=serialize(qs), width=width, type='primitive', path=path, template=template)
                            else:
                                data = qs.serialize(path=path, wrap=wrap, lazy=lazy)
                            data.update(name=verbose_name, key=attr_name)
                        else:
                            if self.metadata['primitive'] and deep > 0:  # one-to-many or many-to-many (and deep > 0)
                                data = dict(value=serialize(qs), width=width, type='primitive', path=path, template=template)
                            else:
                                data = qs.to_list(detail=False)
                    elif isinstance(value, QuerySetStatistics):
                        statistics = value
                        verbose_name = getattr(attr, '__verbose_name__', statistics.metadata['verbose_name'])
                        if verbose_name is None:
                            verbose_name = pretty(attr_name)
                        statistics.contextualize(self.request)
                        data = statistics.serialize(path=path, wrap=wrap, lazy=lazy)
                        data.update(name=verbose_name, key=attr_name) if wrap else None
                    elif isinstance(value, ValueSet):
                        valueset = value
                        verbose_name = getattr(attr, '__verbose_name__', valueset.metadata['verbose_name'])
                        if verbose_name is None:
                            verbose_name = pretty(attr_name)
                        valueset.contextualize(self.request)
                        value.metadata['printing'] = self.metadata['printing']
                        key = attr_name
                        inner_deep = 0 if self.metadata['attr'] or (deep==1 and i==0) else deep+1
                        valueset.path = path
                        valueset.load(wrap=wrap, detail=wrap or detail, deep=inner_deep)
                        if not valueset:
                            continue
                        refresh = valueset.refresh_data()
                        collapsed = valueset.metadata['collapsed']
                        data = dict(uuid=uuid1().hex, type='fieldset', name=verbose_name,
                            key=key, refresh=refresh, actions=[], inline_actions=[], data=valueset, path=path, collapsed=collapsed
                        ) if wrap else valueset
                        if self.request and self.request.path.startswith('/app/'):
                            data.update(instance=valueset.instance)
                        if wrap:
                            for action_type in ('actions', 'inline_actions'):
                                for form_name in valueset.metadata[action_type]:
                                    form_cls = self.instance.action_form_cls(form_name)
                                    if form_cls.check_fake_permission(self.request, valueset.instance, self.instance):
                                        data[action_type].append(form_cls.get_metadata(path))
                            data.update(path=path)
                            if valueset.metadata['image']:
                                image = valueset.metadata['image']
                                if image:
                                    image = str(image)
                                    if not image.startswith('/') and not image.startswith('http'):
                                        image = '/media/{}'.format(image)
                                    data.update(image=image)
                            if valueset.metadata['template']:
                                data.update(template='{}.html'.format(valueset.metadata['template']))
                    else:
                        path = '{}{}/'.format(self.path, attr_name)
                        data = value
                        verbose_name = pretty(self.metadata['model'].get_attr_metadata(attr_name)[0])
                        self.metadata['primitive'] = True
                        if not is_app:
                            data = serialize(data)
                        if wrap or detail:
                            template = getattr(attr, '__template__', None)
                            metadata = getattr(attr, '__metadata__', None)
                            if template:
                                template = 'renderers/{}.html'.format(template)
                            data = dict(key=attr_name, name=verbose_name, value=data, width=width, template=template, metadata=metadata, type='primitive', path=path)
                    # if verbose:
                    #     attr_name = verbose_name or pretty(self.metadata['model'].get_attr_metadata(attr_name)[0])
                    self[attr_name] = data
        elif isinstance(self.instance, Model):
            self['id'] = self.instance.id
            self[self.metadata['model'].__name__.lower()] = str(self.instance)

        return self

    def __str__(self):
        if self.request:
            return self.html()
        return json.dumps(self, indent=4, ensure_ascii=False)

    def __repr__(self):
        return 'Valueset <{}>'.format(self.instance)

    def serialize(self, wrap=False):
        self.load(wrap=wrap, detail=wrap)
        if wrap:
            check_fieldsets_type(self)
            # print(json.dumps(data, indent=4, ensure_ascii=False))
            if isinstance(self.instance, QuerySet):
                name = self.instance.model.metaclass().verbose_name_plural
                icon = getattr(self.instance.model.metaclass(), 'icon', None)
            elif isinstance(self.instance, Model):
                name = str(self.instance)
                icon = getattr(self.instance.metaclass(), 'icon', None)
            else:
                name = ''
                icon = None
            output = dict(
                uuid=uuid1().hex, type='object', name=name
            )
            if self.request and self.request.path.startswith('/app/'):
                output.update(instance=self.instance)
            for key in ('title', 'subtitle', 'status'):
                if self.metadata[key]:
                    value = getattr(self.instance, self.metadata[key])
                    value = value() if callable(value) else value
                    verbose_name, ordering, template, metadata = self.instance.get_attr_metadata(self.metadata[key])
                    if isinstance(value, QuerySet):
                        value = [str(obj) for obj in value]
                    output[key] = dict(value=value, template=template, metadata=metadata)
            is_app = self.request and self.request.path.startswith('/app/')
            output.update(icon=icon, data=self, actions=[], inline_actions=[], attach=[], append={})
            for action_type in ('actions', 'inline_actions'):
                for form_name in self.metadata[action_type]:
                    form_cls = self.instance.action_form_cls(form_name)
                    if self.request is None or form_cls.check_fake_permission(
                            request=self.request, instance=self.instance, instantiator=self.instance,
                    ):
                        output[action_type].append(form_cls.get_metadata(self.path))
            for attr_name in self.metadata['attach']:
                name = getattr(self.instance, attr_name)().metadata['verbose_name'] or pretty(attr_name)
                if self.request is None or self.instance.has_attr_permission(self.request.user, attr_name):
                    output['attach'].append(dict(name=name, path='{}{}/'.format(self.path, attr_name)))
            for position, attr_names in self.metadata['append'].items():
                for attr_name in attr_names:
                    if self.request is None or self.instance.has_attr_permission(self.request.user, attr_name):
                        template = getattr(getattr(self.instance, attr_name), '__template__', None)
                        if position not in output['append']:
                            output['append'][position] = {}
                        output['append'][position].update(
                            self.instance.value_set(attr_name).renderer(template).contextualize(self.request).load(wrap=wrap)
                        )
            return output
        else:
            if len(self.metadata['names']) == 1:
                return self[list(self.metadata['names'].keys())[0]]
            return self

    def html(self, path=None, print=False):
        self.path = path if path else self.path
        self.metadata['printing'] = True
        serialized = self.serialize(wrap=True)
        if self.metadata['attr']:
            is_ajax = self.request.headers.get('x-requested-with') == 'XMLHttpRequest'
            is_modal = 'modal' in self.request.GET
            data = serialized['data'][next(iter(serialized['data']))]
            if data['type'] in ('fieldset-list', 'fieldset-group'):
                data['name'] = serialized['name']
                data['icon'] = serialized['icon']
            if data['type']=='fieldset':
                if is_ajax and not is_modal:
                    # if 'tab' in self.request.GET: data['name'] = None
                    template_name = 'valueset/fieldset.html'
                else:
                    template_name, data = 'valueset/valueset.html', serialized
            elif data['type']=='fieldset-list':
                if self.metadata['source'] or is_modal:
                    template_name = 'valueset/valueset.html'
                else:
                    template_name = 'valueset/fieldset-tab.html'
            elif data['type']=='queryset':
                if self.metadata['source'] or is_modal:
                    template_name, data = 'valueset/valueset.html', serialized
                else:
                    # if 'tab' in self.request.GET: data['name'] = None
                    template_name = 'queryset/queryset.html'
            elif data['type']=='statistics':
                if self.metadata['source'] or is_modal:
                    template_name, data = 'valueset/valueset.html', serialized
                else:
                    # if 'tab' in self.request.GET: data['name'] = None
                    template_name = 'queryset/statistics.html'
            elif data['type'] == 'primitive':
                template_name = 'valueset/primitive.html'
            else:
                template_name = 'valueset/valueset.html'
        else:
            template_name, data = 'valueset/valueset.html', serialized
        # pprint.pprint(data)
        return render_to_string(template_name, dict(data=data, print=print), request=self.request)
