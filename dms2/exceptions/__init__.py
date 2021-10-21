

class ReadyResponseException(BaseException):
    def __init__(self, data):
        self.data = data
        super().__init__()
