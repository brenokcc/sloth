# -*- coding: utf-8 -*-
import json
from uuid import uuid1
import pprint

from django.db.models import Model
from django.template.loader import render_to_string

from sloth.core.queryset import QuerySet
from sloth.core.statistics import QuerySetStatistics
from sloth.utils import getattrr, serialize, pretty


def check_fieldsets_type(item):
    types = 'fieldset', 'fieldset-list', 'fieldset-group'
    for name, subitem in item.items():
        if 'type' in subitem and subitem['type'] in types:
            check_fieldsets_type(subitem['data'])
            subitem['type'] = check_fieldset_type(subitem)


def check_fieldset_type(item):
    if is_fieldset_group(item['data']):
        first = item['data'][next(iter(item['data']))]
        if first['type'] != 'fieldset-lit':
            first['name'] = None
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
    def __init__(self, instance, names, image=None):
        self.request = None
        self.instance = instance
        self.metadata = dict(
            model=type(instance), names={}, metadata=[], actions=[], type=None, attr=None, source=None,
            attach=[], append=[], image=image, template=None, primitive=False, verbose_name=None,
            title=None, subtitle=None, status=None, icon=None, only={}, refresh={},
        )
        for attr_name in names:
            if isinstance(attr_name, tuple):
                for name in attr_name:
                    self.metadata['names'][name] = 100 // len(attr_name)
            else:
                self.metadata['names'][attr_name] = 100
        super().__init__()

    def only(self, name, role=None, roles=()):
        if name not in self.metadata['only']:
            self.metadata['only'][name] = []
        if role:
            self.metadata['only'][name].append(role)
        self.metadata['only'][name].extend(roles)
        return self

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

    def verbose_name(self, name):
        self.metadata['verbose_name'] = pretty(name)
        return self

    def attr(self, name):
        self.metadata['attr'] = name
        return self

    def source(self, name):
        self.metadata['source'] = name
        return self

    def reload(self, seconds=5, condition=None, max_requests=12):
        self.metadata['refresh'] = dict(seconds=seconds, condition=condition, retry=max_requests)
        return self

    def contextualize(self, request):
        self.request = request
        return self

    def debug(self):
        print(json.dumps(self.serialize(wrap=True, verbose=True), indent=4, ensure_ascii=False))

    def apply_role_lookups(self, user):
        return self

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

    def get_path(self, attr_name):
        if isinstance(self.instance, QuerySet):
            metaclass = self.instance.model.metaclass()
            return '/{}/{}/{}/'.format(metaclass.app_label,metaclass.model_name, attr_name)
        metaclass = self.instance.metaclass()
        return '/{}/{}/{}/{}/'.format(metaclass.app_label, metaclass.model_name,self.instance.pk, attr_name)

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

    def load(self, wrap=True, verbose=False, detail=False, deep=0):
        only = []
        is_meta_api = False
        if self.request:
            is_meta_api = self.request.path.startswith('/meta/')
            if 'only' in self.request.GET:
                only.extend(self.request.GET['only'].split(','))
                self.request.GET._mutable = True
                self.request.GET.pop('only')
                self.request.GET._mutable = False

        if self.metadata['names']:
            for i, (attr_name, width) in enumerate(self.metadata['names'].items()):
                if only and attr_name not in only:
                    continue
                if self.request and not self.request.user.is_superuser:
                    if self.metadata['only'] and attr_name in self.metadata['only']:
                        if not self.request.user.roles.contains(*self.metadata['only'][attr_name]):
                            continue
                if self.request is None or self.instance.has_attr_permission(self.request.user, attr_name):
                    lazy = wrap and (deep > 1 or (deep > 0 and i > 0))
                    attr, value = getattrr(self.instance, attr_name)
                    path = self.get_path(attr_name)
                    if isinstance(value, QuerySet) or hasattr(value, '_queryset_class'):  # RelatedManager
                        qs = value if isinstance(value, QuerySet) else value.filter() # ManyRelatedManager
                        qs.metadata['uuid'] = attr_name
                        verbose_name = getattr(attr, '__verbose_name__', qs.metadata['verbose_name'] or pretty(attr_name))
                        qs = qs.contextualize(self.request)
                        if wrap:
                            if self.metadata['primitive']:
                                data = dict(value=serialize(qs), width=width, template=None, type='primitive', path=path)
                            else:
                                data = qs.serialize(path=path, wrap=wrap, verbose=verbose, lazy=lazy)
                            data.update(name=verbose_name if verbose else attr_name, key=attr_name)
                        else:
                            if self.metadata['primitive']:  # one-to-many or many-to-many
                                data = dict(value=serialize(qs), width=width, template=None, type='primitive', path=path)
                            else:
                                data = qs.to_list(detail=False)
                    elif isinstance(value, QuerySetStatistics):
                        statistics = value
                        verbose_name = getattr(attr, '__verbose_name__', statistics.metadata['verbose_name'] or pretty(attr_name))
                        statistics.contextualize(self.request)
                        data = statistics.serialize(path=path, wrap=wrap, lazy=lazy)
                        data.update(name=verbose_name if verbose else attr_name, key=attr_name) if wrap else None
                    elif isinstance(value, ValueSet):
                        valueset = value
                        verbose_name = getattr(attr, '__verbose_name__', valueset.metadata['verbose_name'] or pretty(attr_name))
                        valueset.contextualize(self.request)
                        key = attr_name
                        inner_deep = 0 if self.metadata['attr'] or (deep==1 and i==0) else deep+1
                        valueset.load(wrap=wrap, verbose=verbose, detail=wrap and verbose or detail, deep=inner_deep)
                        if not valueset:
                            continue
                        refresh = valueset.refresh_data()
                        data = dict(uuid=uuid1().hex, type='fieldset', name=verbose_name if verbose else attr_name,
                            key=key, refresh=refresh, actions=[], data=valueset, path=path) if wrap else valueset
                        if wrap:
                            for form_name in valueset.metadata['actions']:
                                form_cls = self.instance.action_form_cls(form_name)
                                if form_cls.check_fake_permission(self.request, self.instance, self.instance):
                                    data['actions'].append(form_cls.get_metadata(path))
                            data.update(path=path)
                            if valueset.metadata['image']:
                                image_attr = getattr(self.instance, valueset.metadata['image'])
                                image = image_attr() if callable(image_attr) else image_attr
                                if image:
                                    image = str(image)
                                    if not image.startswith('/') and not image.startswith('http'):
                                        image = '/media/{}'.format(image)
                                    data.update(image=image)
                            if valueset.metadata['template']:
                                data.update(template='{}.html'.format(valueset.metadata['template']))
                    else:
                        data = value
                        verbose_name = None
                        self.metadata['primitive'] = True
                        if not wrap or is_meta_api:
                            data = serialize(data)
                        if wrap and verbose or detail:
                            template = getattr(attr, '__template__', None)
                            metadata = getattr(attr, '__metadata__', None)
                            if template:
                                template = 'renderers/{}.html'.format(template)
                            data = dict(value=data, width=width, template=template, metadata=metadata, type='primitive', path=path)
                    if verbose:
                        attr_name = verbose_name or pretty(self.metadata['model'].get_attr_metadata(attr_name)[0])
                    self[attr_name] = data
        else:
            self['id'] = self.instance.id
            self[self.metadata['model'].__name__.lower()] = str(self.instance)

        return self

    def __str__(self):
        if self.request:
            return self.html()
        return json.dumps(self, indent=4, ensure_ascii=False)

    def serialize(self, wrap=False, verbose=False):
        self.load(wrap=wrap, verbose=verbose, detail=wrap and verbose)
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
            for key in ('title', 'subtitle', 'status'):
                if self.metadata[key]:
                    value = getattr(self.instance, self.metadata[key])
                    if self.metadata[key]:
                        verbose_name, ordering, template, metadata = self.instance.get_attr_metadata(self.metadata[key])
                    else:
                        verbose_name, ordering, template, metadata = str(self.instance), None, None, {}
                    output[key] = dict(value=value, template=template, metadata=metadata)

            output.update(icon=icon, data=self, actions=[], attach=[], append={})
            for form_name in self.metadata['actions']:
                form_cls = self.instance.action_form_cls(form_name)
                if self.request is None or form_cls.check_fake_permission(
                        request=self.request, instance=self.instance, instantiator=self.instance,
                ):
                    path = '/{}/{}/{}/'.format(
                        self.instance.metaclass().app_label,
                        self.instance.metaclass().model_name, self.instance.pk
                    )
                    output['actions'].append(form_cls.get_metadata(path))
            for attr_name in self.metadata['attach']:
                name = getattr(self.instance, attr_name)().metadata['verbose_name'] or pretty(attr_name)
                path = '/{}/{}/{}/{}/'.format(
                    self.instance.metaclass().app_label,
                    self.instance.metaclass().model_name,
                    self.instance.pk, attr_name
                )
                if self.request is None or self.instance.has_attr_permission(self.request.user, attr_name):
                    output['attach'].append(dict(name=name, path=path))
            for attr_name in self.metadata['append']:
                if self.request is None or self.instance.has_attr_permission(self.request.user, attr_name):
                    output['append'].update(
                        self.instance.values(attr_name).contextualize(
                            self.request
                        ).load(wrap=wrap, verbose=verbose)
                    )
            return output
        else:
            if len(self.metadata['names']) == 1:
                return self[list(self.metadata['names'].keys())[0]]
            return self

    def html(self):
        serialized = self.serialize(wrap=True, verbose=True)
        if self.metadata['attr']:
            is_ajax = self.request.headers.get('x-requested-with') == 'XMLHttpRequest'
            is_modal = 'modal' in self.request.GET
            data = serialized['data'][next(iter(serialized['data']))]
            if data['type'] in ('fieldset-list', 'fieldset-group'):
                data['name'] = serialized['name']
                data['icon'] = serialized['icon']
            if data['type']=='fieldset':
                if is_ajax and not is_modal:
                    data['name'] = None
                    template_name = 'app/valueset/fieldset.html'
                else:
                    template_name, data = 'app/valueset/valueset.html', serialized
            elif data['type']=='fieldset-list':
                if self.metadata['source'] or is_modal:
                    template_name = 'app/valueset/valueset.html'
                else:
                    template_name = 'app/valueset/fieldset-tab.html'
            elif data['type']=='queryset':
                if self.metadata['source'] or is_modal:
                    template_name, data = 'app/valueset/valueset.html', serialized
                else:
                    data['name'] = None
                    template_name = 'app/queryset/queryset.html'
            elif data['type']=='statistics':
                if self.metadata['source'] or is_modal:
                    template_name, data = 'app/valueset/valueset.html', serialized
                else:
                    data['name'] = None
                    template_name = 'app/statistics.html'
            elif data['type'] == 'primitive':
                template_name = 'app/valueset/primitive.html'
            else:
                template_name = 'app/valueset/valueset.html'
        else:
            template_name, data = 'app/valueset/valueset.html', serialized
        # pprint.pprint(data)
        return render_to_string(template_name, dict(data=data), request=self.request)
