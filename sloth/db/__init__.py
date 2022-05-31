# -*- coding: utf-8 -*-

ROLE_DEFINER_CLASSES = set()

def meta(verbose_name=None, renderer=None, **metadata):
    def decorate(func):
        if verbose_name:
            setattr(func, '__verbose_name__', verbose_name)
        if renderer:
            setattr(func, '__template__', renderer)
            setattr(func, '__metadata__', metadata)

        return func
    return decorate


def role(name, username, email=None, active=None, **scopes):
    def decorate(cls):
        if not hasattr(cls, '__roles__'):
            setattr(cls, '__roles__', [])
        roles = getattr(cls, '__roles__')
        roles.append(
            dict(name=name, username=username, email=email, active=active, scopes=scopes)
        )
        ROLE_DEFINER_CLASSES.add(cls)
        return cls
    return decorate
