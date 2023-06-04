from django.core.management.commands.test import Command

from sloth.test import SeleniumTestCase


class Command(Command):

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--step', nargs='+', help='Resume test from a specific step')
        parser.add_argument('--freeze', nargs='+', help='Create dev database from a specific step')
        parser.add_argument('--watch', action="store_true", help='Show the execution in the browser in fast speed')
        parser.add_argument('--explain', action="store_true", help='Show the execution in the browser in slow speed')

    def handle(self, *args, **options):
        step = int(options.get('step')[0]) if options.get('step') else 0
        freeze = int(options.get('freeze')[0]) if options.get('freeze') else None
        if step > 1:
            SeleniumTestCase.RESUME_FROM_STEP = step - 1
        SeleniumTestCase.FREEZE = freeze
        SeleniumTestCase.EXPLAIN = options['explain']
        SeleniumTestCase.HEADLESS = not options['watch']
        super().handle(*args, **options)
