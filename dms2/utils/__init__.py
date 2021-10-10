from django.apps import apps


def getattrr(obj, args):
    if args == '__str__':
        attrs = [args]
    else:
        attrs = args.split('__')
    return _getattr_rec(obj, attrs)


def _getattr_rec(obj, attrs):
    attr_name = attrs.pop(0)
    if obj is not None:
        verbose_name = attr_name
        attr = getattr(obj, attr_name)
        if hasattr(attr, 'verbose_name'):
            verbose_name = attr.verbose_name
        if hasattr(attr, 'all'):
            value = attr.all()
        elif callable(attr):
            value = attr()
        else:
            value = attr
        if attrs:
            return _getattr_rec(value, attrs)
        else:
            return verbose_name, value
    return None


def igetattr(obj, attr):
    for a in dir(obj):
        if a.lower() == attr.lower():
            return getattr(obj, a)


def scan():
    tree = {}
    for model in apps.get_models():
        metadata = getattr(model, '_meta')
        app_label = metadata.app_label
        model_name = metadata.model_name
        for cls in (model, model.objects):
            if hasattr(cls, '_queryset_class'):
                queryset_class = getattr(cls, '_queryset_class')
            else:
                queryset_class = None
            for attr_name, v in (queryset_class or cls).__dict__.items():
                if hasattr(v, 'decorated'):
                    if app_label not in tree:
                        tree[app_label] = {}
                    if model_name not in tree[app_label]:
                        tree[app_label][model_name] = {}
                    if queryset_class:
                        if attr_name not in tree[app_label][model_name]:
                            tree[app_label][model_name][attr_name] = {}
                        if hasattr(v, 'allow'):
                            for form_name in getattr(v, 'allow'):
                                if form_name not in tree[app_label][model_name][attr_name]:
                                    tree[app_label][model_name][attr_name][form_name] = {}
                    else:
                        if '{id}' not in tree[app_label][model_name]:
                            tree[app_label][model_name]['{id}'] = {}
                        tree[app_label][model_name]['{id}'][attr_name] = {}
                        if hasattr(v, 'allow'):
                            for form_name in getattr(v, 'allow'):
                                if form_name not in tree[app_label][model_name]['{id}'][attr_name]:
                                    tree[app_label][model_name]['{id}'][attr_name][form_name] = {}
    return tree
