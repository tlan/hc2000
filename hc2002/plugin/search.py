import hc2002.aws.ec2
import hc2002.aws.vpc
import hc2002.plugin as plugin
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

plugin.register_for_resource(__name__, 'hc2002.resource.instance')

class NotFound(Exception): pass

def _search(attribute, criteria, query,
        mappings=None, sort_key=None, item_index=None):

    if not isinstance(criteria, dict):
        return criteria

    parameters = {}
    filters = criteria.copy()

    if mappings:
        for translate_from, translate_to in mappings.iteritems():
            if translate_from in filters:
                parameters[translate_to] = filters.pop(translate_from)

    parameters['filters'] = filters
    logger.info('Searching for %s matching: %s', attribute, parameters)

    results = query(**parameters)
    if not results:
        raise NotFound('No %s matching: %s', attribute, parameters)

    if sort_key:
        results.sort(key=sort_key)

    # 'id' attribute covers the intended use cases; hoist to argument, when it
    # doesn't
    results = [ r.id for r in results ]
    logger.info('Match(es) found: %s' % results)

    if item_index:
        return results[item_index]
    return results

def _multi_search(attribute, items, query,
        mappings=None, sort_key=None, item_index=None):
    single_item = False
    if not isinstance(items, list):
        single_item = True
        items = [ items ]

    results = []
    for item in items:
        search_results = \
                _search(attribute, item, query, mappings, sort_key, item_index)
        if isinstance(search_results, list):
            results.extend(search_results)
        else:
            results.append(search_results)

    if single_item and len(results) == 1:
        return results[0]
    return results

def _image_search(instance):
    if not 'image' in instance:
        return
    ec2 = hc2002.aws.ec2.get_connection()
    instance['image'] = _search('image',
            instance['image'], ec2.get_all_images,
            { 'owner': 'owners', 'executable-by': 'executable_by' },
            lambda x: x.name, -1)

def _security_group_search(instance):
    if not 'security-groups' in instance:
        return
    ec2 = hc2002.aws.ec2.get_connection()
    instance['security-groups'] = _multi_search('security group',
            instance['security-groups'], ec2.get_all_security_groups)

def _snapshot_search(instance):
    if not 'block-devices' in instance:
        return
    ec2 = hc2002.aws.ec2.get_connection()
    for block_device in instance['block-devices'].itervalues():
        if not 'source' in block_device:
            continue
        block_device['source'] = _search('snapshot',
                block_device['source'], ec2.get_all_snapshots,
                { 'owner': 'owner', 'restorable-by': 'restorable_by' },
                lambda x: x.description, -1)

def _subnet_search(instance):
    if not 'subnet' in instance:
        return
    vpc = hc2002.aws.vpc.get_connection()
    instance['subnet'] = _multi_search('subnet', instance['subnet'],
            vpc.get_all_subnets)

# TODO: DescribeNetworkInterfaces

def apply(instance):
    _image_search(instance)
    _security_group_search(instance)
    _snapshot_search(instance)
    _subnet_search(instance)
