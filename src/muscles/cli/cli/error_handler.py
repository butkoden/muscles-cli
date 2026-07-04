

class ConsoleErrorHandler(Exception):

    def handler(self, reason: str | None = None):
        return Exception(reason)
