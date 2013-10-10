import hc2002.plugin as plugin
import hc2002.plugin.user_data
import yaml

plugin.register_for_resource(__name__, 'hc2002.resource.instance')

def apply(instance):
    if 'cloud-config' not in instance:
        return

    if 'user-data' not in instance:
        instance['user-data'] = []
    if isinstance(instance['user-data'], basestring):
        instance['user-data'] = [ instance['user-data'] ]

    instance['user-data'].append('#cloud-config\n' \
            + yaml.safe_dump(instance['cloud-config']))

    del instance['cloud-config']
