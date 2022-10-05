
import re
from logging import StreamHandler
from django.utils.log import DEFAULT_LOGGING


class SqlStreamHandler(StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            msg = re.sub(' +', ' ', msg).replace('\n', '')
            if msg[8:20].startswith('SELECT') and not msg[8:20].startswith('SELECT COUNT'):
                tokens = msg.split(' FROM ')
                msg = '{} SELECT * FROM {}'.format(msg[0:8], tokens[-1])
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            self.handleError(record)


DEFAULT_LOGGING['disable_existing_loggers'] = True
DEFAULT_LOGGING['handlers']['sql'] = {
    'class': 'sloth.utils.log.sql.SqlStreamHandler',
}
DEFAULT_LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['sql'],
    'level': 'DEBUG',
}
