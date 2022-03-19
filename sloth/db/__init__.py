# -*- coding: utf-8 -*-


def meta(verbose_name, template=None, roles=()):
    def decorate(func):
        setattr(func, 'decorated', True)
        setattr(func, 'verbose_name', verbose_name)
        setattr(func, 'template', template)
        setattr(func, 'roles', roles if type(roles) in (str, tuple) else (roles,))
        return func
    return decorate


def role(verbose_name, username, email=None, password=None, **scopes):
    def decorate(cls):
        if not hasattr(cls, '_roles'):
            setattr(cls, '_roles', [])
        roles = getattr(cls, '_roles')
        roles.append(
            dict(name=verbose_name, username=username, email=email, password=password, scopes=scopes)
        )
        return cls
    return decorate

