import re

def _translate(translator, result, value):
    if hasattr(translator, '__iter__'):
        for m in translator:
            _translate(m, result, value)
    else:
        translator(result, value)

def translate(translator, source, destination=None):
    if destination is None: destination = {}

    for key, value in source.iteritems():
        if key in translator:
            _translate(translator[key], destination, value)
    return destination

def if_(condition, if_true, if_false):
    def _if_(destination, value):
        if condition(value):
            if_true(destination, value)
        else:
            if_false(destination, value)
    return _if_

def set_key(key, transform=None):
    def _set_key_transform(destination, value):
        destination[key] = transform(value)
    def _set_key(destination, value):
        destination[key] = value
    return _set_key \
            if transform is None \
            else _set_key_transform

def for_each(action):
    def _for_each(destination, value):
        if isinstance(value, basestring):
            action(destination, value)
        else:
            for v in value:
                action(destination, v)
    return _for_each

def append_to(key, transform=None):
    def _append_to(destination, value):
        if transform is not None:
            value = transform(value)
        if key in destination:
            destination[key].append(value)
        else:
            destination[key] = [ value ]
    return _append_to

def switch(options):
    def _switch(destination, value):
        for regex, action in options.iteritems():
            if re.match(regex, value):
                action(destination, value)
                return
    return _switch

def set_value(key, value):
    def _set_value(destination, _):
        destination[key] = value
    return _set_value

def join(key, string=','):
    def _join(destination, value):
        if isinstance(value, basestring):
            value = [ value ]
        destination[key] = string.join(value)
    return _join

def ignore(destination, value):
    pass
