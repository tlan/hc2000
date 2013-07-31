from hc2002.validation import absolute_path, one_or_more, validate_keys, \
        validate_values

_role_policy = one_or_more({
    'action': one_or_more(basestring),
    'resource': one_or_more(basestring),
})

validator = {
    'name': basestring,
    'path': absolute_path,
    'policy': [
        dict,
        validate_values([
            dict,
            validate_keys([ 'allow', 'deny' ]),
            validate_values(_role_policy),
        ]),
    ],
}
