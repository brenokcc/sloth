# -*- coding: utf-8 -*-


def meta(verbose_name, primary=False, auxiliary=False, actions=()):
    def decorate(func):
        setattr(func, 'decorated', True)
        setattr(func, 'verbose_name', verbose_name)
        setattr(func, 'primary', primary)
        setattr(func, 'auxiliary', auxiliary)
        setattr(func, 'allow', (actions,) if isinstance(actions, str) else actions)
        return func

    return decorate
