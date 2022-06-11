from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('sql', nargs='+', type=str)

    def handle(self, *args, **options):
        sql = '\t'.join(options['sql'])
        cursor = connection.cursor()
        cursor.execute(sql)
        if cursor.description:
            self.stdout.write('\t'.join([col[0] for col in cursor.description]))
            for row in cursor.fetchall():
                self.stdout.write('\t'.join([str(x) for x in row]))
        cursor.close()
