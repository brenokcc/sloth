
def meta(verbose_name, primary=False, auxiliary=False):
    def decorate(func):
        setattr(func, 'decorated', True)
        setattr(func, 'verbose_name', verbose_name)
        setattr(func, 'primary', primary)
        setattr(func, 'auxiliary', auxiliary)
        return func
    return decorate


def allow(*actions):
    def decorate(func):
        setattr(func, 'decorated', True)
        setattr(func, 'allow', actions)
        return func
    return decorate
