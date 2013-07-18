from hc2002.validation import absolute_path, at_most_one_of, file_mode, \
        one_of, one_or_more, path, tolerant_dict, url

_file_attributes = [
    tolerant_dict({
        'content':  basestring,
        'source':   url,
        'target':   path,

        'mode':     file_mode,

        'owner':    basestring,
        'group':    basestring,
        'uid':      int,
        'gid':      int,
    }),
    at_most_one_of('content', 'source', 'target'),
    at_most_one_of('owner', 'uid'),
    at_most_one_of('group', 'gid'),
]

validator = one_or_more([
    tolerant_dict({ 'destination': absolute_path, }),
    _file_attributes,
    tolerant_dict({
        'files': one_or_more(
            one_of(
                basestring,
                [
                    _file_attributes,
                    tolerant_dict({ 'filename': path, }),
                ],
            )
        ),
    }),
])
