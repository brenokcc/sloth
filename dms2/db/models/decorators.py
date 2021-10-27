# -*- coding: utf-8 -*-


def meta(verbose_name, formatter=None):
    def decorate(func):
        setattr(func, 'decorated', True)
        setattr(func, 'verbose_name', verbose_name)
        setattr(func, 'formatter', formatter)
        return func
    return decorate
