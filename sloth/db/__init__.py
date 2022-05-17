# -*- coding: utf-8 -*-


def meta(verbose_name=None, renderer=None):
    def decorate(func):
        if verbose_name:
            setattr(func, '__verbose_name__', verbose_name)
        if renderer:
            setattr(func, '__template__', renderer)
        return func
    return decorate


def role(name, username, email=None, password=None, **scopes):
    def decorate(cls):
        if not hasattr(cls, '__roles__'):
            setattr(cls, '__roles__', [])
        roles = getattr(cls, '__roles__')
        roles.append(
            dict(name=name, username=username, email=email, password=password, scopes=scopes)
        )
        return cls
    return decorate
