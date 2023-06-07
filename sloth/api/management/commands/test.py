from django.core.management.commands.test import Command

from sloth.test import SeleniumTestCase


class Command(Command):

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--from', nargs='+', help='Run test from a specific step')
        parser.add_argument('--restore', nargs='+', help='Restore development database from a specific step')
        parser.add_argument('--browser', action="store_true", help='Run test in the browser in fast speed')
        parser.add_argument('--tutorial', action="store_true", help='Run test in the browser in slow speed')
        parser.add_argument('--write', action="store_true", help='Log browser actions in the terminal')

    def handle(self, *args, **options):
        from_step = int(options.get('from')[0]) if options.get('from') else 0
        restore = int(options.get('restore')[0]) if options.get('restore') else None
        if from_step > 1:
            SeleniumTestCase.FROM_STEP = from_step - 1
        SeleniumTestCase.RESTORE = restore
        SeleniumTestCase.EXPLAIN = options['tutorial']
        SeleniumTestCase.LOG_ACTION = 1 if options['write'] else 0
        SeleniumTestCase.HEADLESS = not options['browser'] and not options['tutorial'] and not options['write']
        super().handle(*args, **options)
