import datetime

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

_scheduled_group_action = {
    'count':        int,
    'min-count':    int,
    'max-count':    int,
    'start-time':   datetime.datetime,
    'end-time':     datetime.datetime,
    'recurrence':   basestring,
}

_notification_configuration = {
    'topic':    basestring,
    'type':     one_or_more(basestring),
}

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

    # Spot instances
    'spot-price':               float,
    'spot-request-type':        basestring,
    'valid-from':               basestring,
    'valid-until':              basestring,
    'launch-group':             basestring,
    'availability-zone-group':  basestring,

    # Auto-scaling groups
    'auto-scaling-group':           basestring,
    'launch-configuration':         basestring,
    'auto-scaling-cooldown':        int,
    'auto-scaling-grace-period':    int,
    'auto-scaling-health-check':    basestring,
    'load-balancers':               one_or_more(basestring),
    'termination-policies':         one_or_more(basestring),
    'schedule':                     validate_values(_scheduled_group_action),
    'notification':                 _notification_configuration,
}

_run_instance_keys = [
    'instance-type',
    'ebs-optimized',
    'block-devices',
    'image',
    'kernel',
    'ramdisk',
    'min-count',
    'max-count',
    'count',
    'tags',
    'key',
    'role',
    'security-groups',
    'subnet',
    'ip-address',
    'availability-zone',
    'placement-group',
    'tenancy',
    'user-data',
    'monitoring',
    'api-termination',
    'shutdown-behavior',
    'client-token',
]

_spot_instance_keys = [
    'instance-type',
    'ebs-optimized',
    'block-devices',
    'image',
    'kernel',
    'ramdisk',
    'count',
    'key',
    'role',
    'security-groups',
    'subnet',
    'availability-zone',
    'placement-group',
    'user-data',
    'monitoring',
    'spot-price',
    'spot-request-type',
    'valid-from',
    'valid-until',
    'launch-group',
    'availability-zone-group',
]

_launch_config_keys = [
    'launch-configuration',
    'instance-type',
    'spot-price',
    'image',
    'kernel',
    'ramdisk',
    'key',
    'role',
    'security-groups',
    'user-data',
    'monitoring',
    'ebs-optimized',
    'block-devices',
]

_auto_scaling_group_keys = [
    'auto-scaling-group',
    'launch-configuration',
    'count',
    'min-count',
    'max-count',
    'subnet',
    'availability-zone',
    'auto-scaling-cooldown',
    'auto-scaling-grace-period',
    'auto-scaling-health-check',
    'load-balancers',
    'tags',
    'termination-policies',
    'schedule',
    'notification',
]

_resolvable_prefixes = ('availability-zone:', 'image:', 'kernel:', 'key:',
        'load-balancers:', 'ramdisk:', 'security-groups:', 'spot-price:',
        'subnet:')

validator = [
    dict,
    tolerant_dict(_instance_dict),
    one_of(
        validate_keys(one_of(
            in_(_run_instance_keys),
            prefix(_resolvable_prefixes),
        )),
        validate_keys(one_of(
            in_(_spot_instance_keys),
            prefix(_resolvable_prefixes),
        )),
        validate_keys(one_of(
            in_(_launch_config_keys + _auto_scaling_group_keys),
            prefix(_resolvable_prefixes),
        )),
    ),
]
