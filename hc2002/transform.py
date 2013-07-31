import re

def match(pattern):
    regex = re.compile(pattern)
    def _match(value):
        return regex.match(value)
    return _match

