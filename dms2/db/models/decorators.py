# -*- coding: utf-8 -*-


def meta(verbose_name, formatter=None):
    def decorate(func):
        setattr(func, 'decorated', True)
        setattr(func, 'verbose_name', verbose_name)
        setattr(func, 'formatter', formatter)
        return func
    return decorate


def role(verbose_name, user, **scopes):
    def decorate(cls):
        if not hasattr(cls, '_roles'):
            setattr(cls, '_roles', [])
        roles = getattr(cls, '_roles')
        roles.append(
            dict(name=verbose_name, user=user, scopes=scopes)
        )
        return cls
    return decorate
