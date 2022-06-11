import inspect
from ..actions import ACTIONS
from .valueset import ValueSet
from django.utils import termcolors


def bold(text):
    return termcolors.colorize(text, opts=('bold',))


def warning(message):
    print(termcolors.colorize('WARNING', fg='yellow', opts=('bold',)), message)


def validate_model(model):
    validate_valueset(model(pk=0).view())
    validate_queryset(model.objects.all())


def validate_valueset(valueset, method='view'):
    for name in valueset.metadata['names'].keys():
        try:
            try:
                attr = getattr(valueset.instance, name)
            except AttributeError as e:
                if type(e) == AttributeError:
                    warning('The meta attribute "{}" used in the method {}() of class {} does not exist.'.format(
                         bold(name), bold(method), bold(type(valueset.instance).__name__))
                    )
                continue
        except BaseException:
            continue
        if inspect.ismethod(attr):
            try:
                attr = attr()
                if isinstance(attr, ValueSet):
                    validate_valueset(attr, name)
            except BaseException:
                continue
    for name in valueset.metadata['actions']:
        if name.lower() not in ('add', 'edit', 'delete'):
            if name not in ACTIONS:
                warning('The action "{}" used in the method {}() of model {} does not exist.'.format(
                    bold(name), bold(method), bold( type(valueset.instance).__name__))
                )


def validate_queryset(qs, method='all'):
    for key in ('actions', 'global_actions', 'batch_actions'):
        for name in qs.metadata[key]:
            if name.lower() not in ('add', 'edit', 'delete'):
                if name not in ACTIONS:
                    warning('The action "{}" used in the method {}() of manager {} does not exist.'.format(
                        bold(name), bold(method), bold(type(qs).__name__))
                    )