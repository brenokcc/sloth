from dms2.formatters import Formatter


class Progress(Formatter):
    template = 'adm/formatters/progress.html'

    def render(self):
        return super().render()
