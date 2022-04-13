# -*- coding: utf-8 -*-


def verbose_name(name, template=None):
    def decorate(func):
        setattr(func, '__verbose_name__', name)
        setattr(func, '__template__', template)
        return func
    return decorate


def role(name, username, email=None, password=None, **scopes):
    def decorate(cls):
        if not hasattr(cls, '_roles'):
            setattr(cls, '_roles', [])
        roles = getattr(cls, '_roles')
        roles.append(
            dict(name=name, username=username, email=email, password=password, scopes=scopes)
        )
        return cls
    return decorate

