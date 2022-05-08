# -*- coding: utf-8 -*-


def verbose_name(name):
    def decorate(func):
        setattr(func, 'decorated', True)
        setattr(func, '__verbose_name__', name)
        return func
    return decorate


def template(name):
    def decorate(func):
        setattr(func, 'decorated', True)
        setattr(func, '__template__', name)
        return func
    return decorate


def role(name, username, email=None, password=None, **scopes):
    def decorate(cls):
        setattr(cls, 'decorated', True)
        if not hasattr(cls, '__roles__'):
            setattr(cls, '__roles__', [])
        roles = getattr(cls, '__roles__')
        roles.append(
            dict(name=name, username=username, email=email, password=password, scopes=scopes)
        )
        return cls
    return decorate

