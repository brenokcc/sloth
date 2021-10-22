

class ReadyResponseException(BaseException):
    def __init__(self, data):
        self.data = data
        super().__init__()


class HtmlReadyResponseException(BaseException):
    def __init__(self, html):
        self.html = html
        super().__init__()
