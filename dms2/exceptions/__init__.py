
class ReadyResponseException(BaseException):
    def __init__(self, response):
        self.response = response
        super().__init__()


class JsonReadyResponseException(BaseException):
    def __init__(self, data):
        self.data = data
        super().__init__()


class HtmlJsonReadyResponseException(BaseException):
    def __init__(self, html):
        self.html = html
        super().__init__()
