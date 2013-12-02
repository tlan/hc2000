import hc2002.aws.vpc
import hc2002.plugin as plugin
import hc2002.plugin.search
import re

plugin.register_for_resource(__name__, 'hc2002.resource.instance')

def _process_security_group(vpc_id, security_group):
    if isinstance(security_group, basestring):
        if not re.match('sg-[0-9a-f]*', security_group):
            security_group = { 'group-name': security_group }
    if isinstance(security_group, dict):
        security_group['vpc-id'] = vpc_id
    return security_group

def _process_subnet(vpc_id, subnet):
    if isinstance(subnet, dict):
        subnet['vpc-id'] = vpc_id
    return subnet

def _process_one_or_more(vpc_id, values, process_function):
    single_item = False
    if not isinstance(values, list):
        single_item = True
        values = [ values ]

    results = []
    for value in values:
        results.append(process_function(vpc_id, value))

    if single_item:
        results = results[0]

    return results

def apply(instance):
    if not 'vpc' in instance:
        return

    if isinstance(instance['vpc'], dict):
        vpc = hc2002.aws.vpc.get_connection()
        instance['vpc'] = hc2002.plugin.search._search('VPC',
                instance['vpc'], vpc.get_all_vpcs)[0]

    vpc_id = instance.pop('vpc')

    if 'security-groups' in instance:
        instance['security-groups'] = _process_one_or_more(vpc_id,
                instance['security-groups'], _process_security_group)
    if 'subnet' in instance:
        instance['subnet'] = _process_one_or_more(vpc_id,
                instance['subnet'], _process_subnet)
