import boto.ec2.blockdevicemapping
import boto.exception
import datetime
import sys
import time
import logging

import hc2002.aws.auto_scaling
import hc2002.aws.ec2
import hc2002.plugin
import hc2002.resource.load_balancer
import hc2002.transform as xf
import hc2002.translation as xl
from hc2002.validation import at_most_one_of, in_, match, one_of, \
        one_or_more, prefix, validate, validate_keys, validate_values, \
        tolerant_dict

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

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
    'user-data':            basestring,
    'monitoring':           bool,
    'api-termination':      bool,
    'shutdown-behavior':    one_of(
                                match('stop'),
                                match('terminate')),
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

validator = [
    dict,
    tolerant_dict(_instance_dict),
    one_of(
        [
            validate_keys(in_(_run_instance_keys)),
            at_most_one_of('count', 'min_count'),
            at_most_one_of('count', 'max_count'),
        ],
        validate_keys(in_(_spot_instance_keys)),
        validate_keys(in_(_launch_config_keys + _auto_scaling_group_keys)),
    ),
]

_block_device_mapping = {
    'source':       xl.switch({
                        'no-device':            xl.set_value('no_device', True),
                        'ephemeral[0-9]':       xl.set_key('ephemeral_name'),
                        'snap-[a-fA-F0-9]*':    xl.set_key('snapshot_id'),
                    }),
    'size':         xl.set_key('size'),
    'iops':         [
                        xl.set_key('iops'),
                        xl.set_value('volume_type', 'io1')
                    ],
    'disposable':   xl.set_key('delete_on_termination'),
}

def _xl_block_devices(key):
    def _block_devices(destination, value):
        bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping()
        for k, v in value.iteritems():
            params = xl.translate(_block_device_mapping, v,
                    { 'delete_on_termination': True })
            bdm[k] = boto.ec2.blockdevicemapping.BlockDeviceType(**params)
        destination[key] = bdm

    return _block_devices

def _xl_as_block_devices(key):
    translator = _xl_block_devices(key)

    def _as_block_devices(destination, value):
        translator(destination, value)
        destination[key] = [ destination[key] ]

    return _as_block_devices

# boto.ec2.autoscale.Tag unconditionally outputs optional parameters ResourceId
# and ResourceType, requiring them to be set. _Tag works around that
# constraint.
class _Tag:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def build_params(self, params, i):
        prefix = 'Tags.member.%d.' % i
        params[prefix + 'Key'] = self.key
        params[prefix + 'Value'] = self.value

def _xl_as_tags(destination, value):
    tags = []
    for k, v in value.iteritems():
        tags.append(_Tag(k, v))
    destination['tags'] = tags

_launch_instance_mapping = {
    'instance-type':        xl.set_key('instance_type'),
    'ebs-optimized':        xl.set_key('ebs_optimized'),
    'block-devices':        _xl_block_devices('block_device_map'),
    'image':                xl.set_key('image_id'),
    'kernel':               xl.set_key('kernel_id'),
    'ramdisk':              xl.set_key('ramdisk_id'),
    'min-count':            xl.set_key('min_count'),
    'max-count':            xl.set_key('max_count'),
    'count':                [
                                xl.set_key('min_count'),
                                xl.set_key('max_count'),
                            ],
    'key':                  xl.set_key('key_name'),
    'role':                 xl.if_(xf.match('arn:aws:iam::'),
                                xl.set_key('instance_profile_arn'),
                                xl.set_key('instance_profile_name')),
    'security-groups':      xl.for_each(
                                xl.if_(xf.match('sg-[0-9A-Fa-f]+$'),
                                    xl.append_to('security_group_ids'),
                                    xl.append_to('security_groups'))),
    'subnet':               xl.set_key('subnet_id'),
    'ip-address':           xl.set_key('private_ip_address'),
    'availability-zone':    xl.set_key('placement'),
    'placement-group':      xl.set_key('placement_group'),
    'tenancy':              xl.set_key('tenancy'),
    'user-data':            xl.set_key('user_data'),
    'monitoring':           xl.set_key('monitoring_enabled'),
    'api-termination':      xl.set_key('disable_api_termination', lambda x: not x),
    'shutdown-behavior':    xl.set_key('instance_initiated_shutdown_behavior'),
    'client-token':         xl.set_key('client_token'),
}

_launch_spot_instance_mapping = _launch_instance_mapping.copy()
# RunInstance arguments not supported in SpotRequests
for key in [ 'min-count', 'max-count', 'ip-address', 'tenancy',
        'api-termination', 'shutdown-behavior', 'client-token' ]:
    del _launch_spot_instance_mapping[key]
# Configuration specific to SpotRequests
_launch_spot_instance_mapping.update({
    'spot-price':               xl.set_key('price'),
    'spot-request-type':        xl.set_key('type'),
    'valid-from':               xl.set_key('valid_from'),
    'valid-until':              xl.set_key('valid_until'),
    'launch-group':             xl.set_key('launch_group'),
    'availability-zone-group':  xl.set_key('availability_zone_group'),
})

_create_launch_configuration_mapping = {
    'launch-configuration':     xl.set_key('name'),
    'instance-type':            xl.set_key('instance_type'),
    'spot-price':               xl.set_key('spot_price'),
    'image':                    xl.set_key('image_id'),
    'kernel':                   xl.set_key('kern_id'),
    'ramdisk':                  xl.set_key('ramdisk_id'),
    'key':                      xl.set_key('key_name'),
    'role':                     xl.set_key('instance_profile_name'),
    'security-groups':          xl.for_each(xl.append_to('security_groups')),
    'user-data':                xl.set_key('user_data'),
    'monitoring':               xl.set_key('instance_monitoring'),
    'ebs-optimized':            xl.set_key('ebs_optimized'),
    'block-devices':            _xl_as_block_devices('block_device_mappings'),
}

_create_auto_scaling_group_mapping = {
    'auto-scaling-group':           xl.set_key('name'),
    'launch-configuration':         xl.set_key('launch_config'),
    'count':                        xl.set_key('desired_capacity'),
    'min-count':                    xl.set_key('min_size'),
    'max-count':                    xl.set_key('max_size'),
    'subnet':                       xl.join('vpc_zone_identifier'),
    'availability-zone':            xl.for_each(xl.append_to('availability_zones')),
    'auto-scaling-cooldown':        xl.set_key('default_cooldown'),
    'auto-scaling-grace-period':    xl.set_key('health_check_period'),
    'auto-scaling-health-check':    xl.set_key('health_check_type'),
    'load-balancers':               xl.for_each(xl.append_to('load_balancers')),
    'tags':                         _xl_as_tags,
    'termination-policies':         xl.for_each(xl.append_to('termination_policies')),
}

# TODO: NetworkInterface

def _setup_auto_scaling_connection():
    global auto_scaling
    auto_scaling = hc2002.aws.auto_scaling.get_connection()

def _setup_ec2_connection():
    global ec2
    ec2 = hc2002.aws.ec2.get_connection()

_scheduled_auto_scaling_action = {
    'count':        xl.set_key('DesiredCapacity'),
    'min-count':    xl.set_key('MinSize'),
    'max-count':    xl.set_key('MaxSize'),
    'start-time':   xl.set_key('StartTime'),
    'end-time':     xl.set_key('EndTime'),
    'recurrence':   xl.set_key('Recurrence'),
}

def _try_and_retry(message, operation, condition, retries=5):

    result = None
    attempt = 0
    msg_suffix = ''
    while True:
        logging.debug(message + msg_suffix)
        try:
            result = operation()
            break
        except boto.exception.BotoServerError as err:
            attempt += 1
            if retries <= attempt \
                    or not condition(err):
                raise

            # Sleep on it
            msg_suffix = ' retry %i' % attempt
            time.sleep(10)

    return result

def _launch_auto_scaling_group(instance):
    _setup_auto_scaling_connection()

    group_name = instance['auto-scaling-group']
    launcher = instance['launch-configuration']

    launcher = auto_scaling.get_all_launch_configurations(names=[ launcher ])
    if len(launcher) == 0:
        params = xl.translate(_create_launch_configuration_mapping, instance)
        launcher = boto.ec2.autoscale.launchconfig.LaunchConfiguration(
                auto_scaling, **params)
        _try_and_retry("Creating launch configuration",
                lambda: auto_scaling.create_launch_configuration(launcher),
                lambda err: err.status == 400 and err.error_message.startswith(
                        'Invalid IamInstanceProfile: '))
    else:
        logger.debug('Launch configuration %s already exists, skipping', launcher)

    group = auto_scaling.get_all_groups(names=[ group_name ])
    if len(group) == 0:
        # TODO: Make this a plugin
        if 'load-balancers' in instance:
            lb = instance['load-balancers']
            if not isinstance(lb, list):
                lb = [ lb ]
            logger.debug('Checking that load balancers exist: %s', lb)
            hc2002.resource.load_balancer.list(lb)

        params = xl.translate(_create_auto_scaling_group_mapping, instance)
        group = boto.ec2.autoscale.group.AutoScalingGroup(
                auto_scaling, **params)
        auto_scaling.create_auto_scaling_group(group)
    else:
        logger.debug('Auto-scaling group already exists, skipping')

    # TODO: Handle load balancers
    # TODO: Handle updates to both launch configuration and group

    if 'notification' in instance:
        notification = instance['notification']
        if not isinstance(notification['type'], list):
            notification['type'] = [ notification['type'] ]
        auto_scaling.put_notification_configuration(group_name,
                notification['topic'], notification['type'])

    if 'schedule' in instance:
        for name, schedule in instance['schedule'].iteritems():
            params = xl.translate(_scheduled_auto_scaling_action, schedule)
            params['AutoScalingGroupName'] = group_name
            params['ScheduledActionName'] = name

            response = auto_scaling.make_request(
                    'PutScheduledUpdateGroupAction', params)
            if response.status != 200:
                logger.warning('Failed to schedule %s scaling action', name)
                logger.warning(response.read())

    return True

def _launch_spot_instance(instance):
    _setup_ec2_connection()

    params = xl.translate(_launch_spot_instance_mapping, instance)
    return _try_and_retry("Creating spot instance request",
            lambda: ec2.request_spot_instances(**params),
            lambda err: err.status == 400 and err.error_message.endswith(
                'Invalid IAM Instance Profile name'))

def _launch_instance(instance):
    _setup_ec2_connection()

    params = xl.translate(_launch_instance_mapping, instance)
    reservation = _try_and_retry("Launching instances",
            lambda: ec2.run_instances(**params),
            lambda err: err.status == 400 and err.error_message.endswith(
                'Invalid IAM Instance Profile name'))

    if 'tags' in instance:
        instances = [ inst.id for inst in reservation.instances ]
        _try_and_retry("Adding tags to instance(s)",
                lambda: ec2.create_tags(instances, instance['tags']),
                lambda err: err.status == 400
                        and err.error_code == 'InvalidInstanceID.NotFound')

    return reservation

def launch(instance):
    hc2002.plugin.apply_for_resource(__name__, instance)
    validate(validator, instance)

    if 'auto-scaling-group' in instance \
            and instance['auto-scaling-group']:
        return _launch_auto_scaling_group(instance)
    elif 'spot-price' in instance \
            and instance['spot-price']:
        return _launch_spot_instance(instance)
    else:
        return _launch_instance(instance)
