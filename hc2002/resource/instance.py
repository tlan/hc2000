from hc2002.validation import in_, match, one_of, one_or_more, prefix, \
        validate_keys, validate_values, tolerant_dict

_block_device = [
    dict,
    validate_values({
        'source':       one_of(
                            match('no-device'),
                            match('ephemeral[0-9]'),
                            match('snap-[a-fA-F0-9]+')),
        'size':         int,
        'iops':         int,
        'disposable':   bool,
    }),
]

_instance_dict = {
    'instance-type':        basestring,
    'ebs-optimized':        bool,
    'block-devices':        _block_device,
    'image':                basestring,
    'kernel':               basestring,
    'ramdisk':              basestring,
    'min-count':            int,
    'max-count':            int,
    'count':                int,
    'tags':                 dict,
    'key':                  basestring,
    'role':                 one_or_more(basestring),
    'security-groups':      one_or_more(basestring),
    'subnet':               one_or_more(match('subnet-[0-9a-fA-F]+')),
    'ip-address':           match('[0-9]{1,3}(\.[0-9]{1,3}){3}'),
    'availability-zone':    one_or_more(basestring),
    'placement-group':      basestring,
    'tenancy':              basestring,
    'user-data':            one_or_more(basestring),
    'monitoring':           bool,
    'api-termination':      bool,
    'shutdown-behavior':    bool,
    'client-token':         basestring,
}

_resolvable_prefixes = ('image:', 'kernel:', 'key:', 'load-balancers:',
    'ramdisk:', 'security-groups:', 'spot-price:', 'subnet:')

validator = [
    dict,
    tolerant_dict(_instance_dict),
    validate_keys(one_of(
        in_(_instance_dict.keys()),
        prefix(_resolvable_prefixes),
    )),
]
