# -*- coding: utf-8 -*-


def meta(verbose_name):
    def decorate(func):
        setattr(func, 'decorated', True)
        setattr(func, 'verbose_name', verbose_name)
        return func

    return decorate
