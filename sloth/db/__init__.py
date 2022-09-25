# -*- coding: utf-8 -*-
from sloth import meta

ROLE_DEFINER_CLASSES = set()

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
