import boto.ec2.blockdevicemapping
import datetime
import email.mime.base
import email.mime.multipart

import hc2002.aws.auto_scaling
import hc2002.aws.ec2
import hc2002.resource.load_balancer
import hc2002.transform as xf
import hc2002.translation as xl
from hc2002.validation import in_, match, one_of, one_or_more, prefix, \
        validate, validate_keys, validate_values, tolerant_dict

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

_ec2_block_device_mapping = {
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

# For BlockDeviceMappings in LaunchConfigurations, use AWS parameter names
# directly to work around boto bug
_as_block_device_mapping = {
    'source':       xl.switch({
                        'ephemeral[0-9]':       xl.set_key('VirtualName'),
                        'snap-[a-fA-F0-9]*':    xl.set_key('Ebs.SnapshotId'),
                    }),
    'size':         xl.set_key('Ebs.VolumeSize'),
}

def _xl_ec2_block_devices(key):
    def _block_devices(destination, value):
        bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping()
        for k, v in value.iteritems():
            params = xl.translate(_ec2_block_device_mapping, v,
                    { 'delete_on_termination': True })
            bdm[k] = boto.ec2.blockdevicemapping.BlockDeviceType(**params)
        destination[key] = bdm

    return _block_devices

def _xl_as_block_devices(key):
    def _block_devices(destination, value):
        mappings = []
        for k, v in value.iteritems():
            # boto.ec2.autoscale.launchconfig.BlockDeviceMapping does not get
            # properly propagated to API call
            bdm = xl.translate(_as_block_device_mapping, v)
            bdm['DeviceName'] = k
            mappings.append(bdm)
        destination[key] = mappings

    return _block_devices

# TODO: Move user-data processing to its own plugin
_magic_to_mime = {
    '#!':               ('text', 'x-shellscript'),
    '#cloud-boothook':  ('text', 'cloud-boothook'),
    '#cloud-config':    ('text', 'cloud-config'),
    '#include':         ('text', 'x-include-url'),
    '#manifest':        ('text', 'hc2000-manifest'),
    '#part-handler':    ('text', 'part-handler'),
    '#puppet':          ('text', 'puppet'),
    '#upstart-job':     ('text', 'upstart-job'),
}

def _xl_user_data(key):
    def _user_data_file(filename):
        with open(filename, 'rb') as f:
            filename = os.path.basename(filename)
            return _user_data_entry(f.read(), filename)

    def _user_data_entry(value, filename=None):
        if value.startswith('file:'):
            return _user_data_file(value[5:])

        maintype, subtype = ('application', 'octet-stream')
        for magic, mime in _magic_to_mime.iteritems():
            if value.startswith(magic):
                maintype, subtype = mime
                break
        if maintype == 'text':
            msg = email.mime.text.MIMEText(value, subtype)
        else:
            msg = email.mime.base.MIMEBase(maintype, subtype)
            msg.set_payload(value)
        if filename:
            msg.add_header('Content-Disposition', 'attachment', filename=filename)
        else:
            msg.add_header('Content-Disposition', 'attachment')
        return msg

    def _user_data(destination, value):
        if isinstance(value, basestring) \
                or not hasattr(value, '__iter__'):
            destination[key] = value
            return

        data = email.mime.multipart.MIMEMultipart()
        for d in value:
            data.attach(_user_data_entry(d))
        destination[key] = data.as_string()

    return _user_data

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
    'block-devices':        _xl_ec2_block_devices('block_device_map'),
    'image':                xl.set_key('image_id'),
    'kernel':               xl.set_key('kernel_id'),
    'ramdisk':              xl.set_key('ramdisk_id'),
    'min-count':            xl.set_key('min_count'),
    'max-count':            xl.set_key('max_count'),
    'count':                xl.set_key('max_count'),
    'tags':                 xl.ignore,
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
    'user-data':            _xl_user_data('user_data'),
    'monitoring':           xl.set_key('monitoring_enabled'),
    'api-termination':      xl.set_key('disable_api_termination', lambda x: not x),
    'shutdown-behavior':    xl.set_key('instance_initiated_shutdown_behavior'),
    'client-token':         xl.set_key('client_token'),
}

_launch_spot_instance_mapping = _launch_instance_mapping.copy()
# RunInstance arguments not supported in SpotRequests
for key in [ 'min-count', 'max-count', 'tags', 'ip-address', 'tenancy',
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
    'user-data':                _xl_user_data('user_data'),
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
    'schedule':                     xl.ignore,
}

# Launch Configurations and Auto-Scaling Groups are meant to share
# configuration, so have them ignore each other's keys.
_launch_configuration_keys = _create_launch_configuration_mapping.keys()
_auto_scaling_group_keys = _create_auto_scaling_group_mapping.keys()

for key in _auto_scaling_group_keys:
    if key not in _create_launch_configuration_mapping:
        _create_launch_configuration_mapping[key] = xl.ignore
for key in _launch_configuration_keys:
    if key not in _create_auto_scaling_group_mapping:
        _create_auto_scaling_group_mapping[key] = xl.ignore

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

def _launch_auto_scaling_group(instance):
    _setup_auto_scaling_connection()

    group_name = instance['auto-scaling-group']
    launcher = instance['launch-configuration']

    launcher = auto_scaling.get_all_launch_configurations(names=[ launcher ])
    if len(launcher) == 0:
        params = xl.translate(_create_launch_configuration_mapping, instance)
        launcher = boto.ec2.autoscale.launchconfig.LaunchConfiguration(
                auto_scaling, **params)
        auto_scaling.create_launch_configuration(launcher)
    else:
        print '=> Launch configuration already exists, skipping'

    group = auto_scaling.get_all_groups(names=[ group_name ])
    if len(group) == 0:
        # TODO: Make this a plugin
        if 'load-balancers' in instance:
            lb = instance['load-balancers']
            if not isinstance(lb, list):
                lb = [ lb ]
            print '* Checking that load balancers exist:', lb
            hc2002.resource.load_balancer.list(lb)

        params = xl.translate(_create_auto_scaling_group_mapping, instance)
        group = boto.ec2.autoscale.group.AutoScalingGroup(
                auto_scaling, **params)
        auto_scaling.create_auto_scaling_group(group)
    else:
        print '=> Auto-scaling group already exists, skipping'

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
                print 'Failed to schedule %s scaling action' % name
                print response.read()

    return True

def _launch_spot_instance(instance):
    _setup_ec2_connection()

    params = xl.translate(_launch_spot_instance_mapping, instance)
    return ec2.request_spot_instances(**params)

def _launch_instance(instance):
    _setup_ec2_connection()

    params = xl.translate(_launch_instance_mapping, instance)
    reservation = ec2.run_instances(**params)

    if 'tags' in instance:
        instances = [ inst.id for inst in reservation.instances ]
        ec2.create_tags(instances, instance['tags'])

    return reservation

def launch(instance):
    validate(validator, instance)

    if 'auto-scaling-group' in instance:
        return _launch_auto_scaling_group(instance)
    elif 'spot-price' in instance:
        return _launch_spot_instance(instance)
    else:
        return _launch_instance(instance)
