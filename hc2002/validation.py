class Context:
    def __init__(self):
        self.scope = []
        self.errors = []

    def current_scope(self):
        return ''.join(self.scope)
    def push_scope(self, scope):
        self.scope.append(scope)
    def pop_scope(self):
        self.scope.pop()

    def error(self, message, value):
        self.errors.append((self.current_scope(), \
                'Expected %s, got %s' % (message, value)))

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

def validate(validator, data):
    context = Context()
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
                context.push_scope('.%s' % k)
                _validate(dict_[k], v, context)
                context.pop_scope()
    return all_of(is_(dict), _tolerant_dict)

def strict_dict(dict_):
    return all_of(tolerant_dict(dict_), validate_keys(dict_.keys()))

def validate_keys(keys):
    def _validate_keys(data, context):
        unknown_keys = []
        for k in data.iterkeys():
            if k not in keys:
                unknown_keys.append(k)
        if len(unknown_keys):
            context.error('Known keys are %s' % keys,
                    unknown_keys)
    return _validate_keys

def validate_values(validator):
    def _validate_values(data, context):
        for k, v in data.iteritems():
            context.push_scope('.%s' % k)
            _validate(validator, v, context)
            context.pop_scope()
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
            context.push_scope('[%i]' % i)
            _validate(validator, element, context)
            context.pop_scope()
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
