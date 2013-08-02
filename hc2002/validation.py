import re

class Context:
    def __init__(self, initial_scope=None):
        self.scope = []
        self.errors = []
        self.error_prefix = []

        if initial_scope is not None:
            self.scope.append(initial_scope)

    def get_scope(self): return ''.join(self.scope)
    def get_error_prefix(self): return ''.join(self.error_prefix)

    def error(self, message, value):
        self.errors.append((self.get_scope(), '%sExpected %s, got %s' \
                % (self.get_error_prefix(), message, value)))

    def __bool__(self):
        return len(self.errors) == 0
    __nonzero__ = __bool__

def as_validator(validator):
    if isinstance(validator, type):
        return is_(validator)
    if isinstance(validator, list):
        return all_of(*validator)
    if isinstance(validator, dict):
        return strict_dict(validator)
    if hasattr(validator, 'validator'):
        return as_validator(validator.validator)
    if validator is None:
        return lambda v, c: None
    return validator

def _validate(validator, data, context):
    as_validator(validator)(data, context)

def validate(validator, data, initial_scope=None):
    context = Context(initial_scope)
    _validate(validator, data, context)
    return context

def is_(expected):
    def _is_(data, context):
        if not isinstance(data, expected):
            context.error('Expected element of type %s' % expected.__name__,
                    data)
    return _is_

def tolerant_dict(dict_):
    def _tolerant_dict(data, context):
        for k, v in data.iteritems():
            if k in dict_:
                context.scope.append('.%s' % k)
                _validate(dict_[k], v, context)
                context.scope.pop()
    return all_of(is_(dict), _tolerant_dict)

def strict_dict(dict_):
    return all_of(tolerant_dict(dict_), validate_keys(in_(dict_.keys())))

def in_(*values):
    if len(values) == 1 \
            and not isinstance(values[0], basestring) \
            and hasattr(values[0], '__iter__'):
        values = values[0]

    def _in_(data, context):
        if data not in values:
            context.error('value in %s' % values, data)
    return _in_

def validate_keys(validator):
    def _validate_keys(data, context):
        unknown_keys = []
        for k in data.iterkeys():
            context.error_prefix.append('Key error. ')
            _validate(validator, k, context)
            context.error_prefix.pop()
    return _validate_keys

def validate_values(validator):
    def _validate_values(data, context):
        for k, v in data.iteritems():
            context.scope.append('.%s' % k)
            _validate(validator, v, context)
            context.scope.pop()
        pass
    return _validate_values

def all_of(*validators):
    def _all_of(data, context):
        errors = len(context.errors)
        for v in validators:
            _validate(v, data, context) 
            if len(context.errors) != errors:
                break
    return _all_of

def one_of(*validators):
    def _one_of(data, context):
        original = len(context.errors)
        for v in validators:
            previous = len(context.errors)
            _validate(v, data, context)
            if previous == len(context.errors):
                del context.errors[original:]
                break
    return _one_of

def at_most_one_of(*keys):
    def _at_most_one_of(data, context):
        matched = 0
        for k in keys:
            matched += k in data
        if matched > 1:
            context.error('At most one of %s expected' % keys, data)
    return _at_most_one_of

def one_or_more(validator):
    def _one_or_more(data, context):
        if not isinstance(data, list):
            return _validate(validator, data, context)
        for i, element in enumerate(data):
            context.scope.append('[%i]' % i)
            _validate(validator, element, context)
            context.scope.pop()
    return _one_or_more

def prefix(prefix):
    def _prefix(data, context):
        if not data.startswith(prefix):
            context.error('prefix %s' % str(prefix), data)
    return _prefix

path = basestring
absolute_path = all_of(path, prefix('/'))
url = basestring

def file_mode(data, context):
    if 0777 != data | 0777:
        context.error("Invalid file mode", data)

def match(pattern):
    regex = re.compile(pattern)
    def _match(data, context):
        if not regex.match(data):
            context.error('Value does not match: %s' % pattern, data)
    return _match
