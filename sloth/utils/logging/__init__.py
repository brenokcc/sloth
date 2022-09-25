import re
from logging import StreamHandler

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