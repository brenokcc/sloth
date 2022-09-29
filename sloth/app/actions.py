import io
import subprocess
from sloth import actions
from django.core.management import call_command


class ExecuteQuery(actions.Action):
    query = actions.TextField()

    class Meta:
        icon = 'chat-left-dots'
        verbose_name = 'Executar SQL'
        modal = False
        style = 'primary'

    def submit(self):
        query = self.cleaned_data['query']
        with io.StringIO() as output:
            call_command('query', query, stdout=output, stderr=output)
            self.output(dict(value=output.getvalue()), 'renderers/programing/strtable.html')

    def has_permission(self, user):
        return user.is_superuser and user.roles.contains('Remote Developer')


class ExecuteScript(actions.Action):
    script = actions.TextField()

    class Meta:
        icon = 'cast'
        verbose_name = 'Executar Script'
        modal = False
        style = 'primary'

    def submit(self):
        script = self.cleaned_data['script']
        p = subprocess.Popen(
            ['python', 'manage.py', 'shell', '-c', script],
            stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate()
        output = '{}{}'.format(stdout.decode(), stderr.decode())
        self.output(dict(value=output), 'renderers/programing/terminal.html')

    def has_permission(self, user):
        return user.is_superuser and user.roles.contains('Remote Developer')