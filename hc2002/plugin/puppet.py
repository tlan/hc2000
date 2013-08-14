import hc2002.config as config
import hc2002.plugin as plugin
import hc2002.plugin.cloud_config
import os.path

plugin.register_for_resource(__name__, 'hc2002.resource.instance')

def _load_manifest(name):
    if not name.endswith('.pp'):
        name = name + '.pp'

    for path in config.puppet_path:
        filename = os.path.join(path, name)
        try:
            with open(filename) as f:
                puppet = f.read()
            if not puppet.startswith('#!/usr/bin/puppet'):
                puppet = '#!/usr/bin/puppet apply\n' + puppet
            return puppet
        except IOError:
            pass

    raise Exception('Couldn\'t find puppet manifest for \'%s\' in %s' \
            % (name, config.puppet_path))

def apply(instance):
    if 'puppet' not in instance:
        return

    if 'user-data' not in instance:
        instance['user-data'] = []
    if isinstance(instance['user-data'], basestring):
        instance['user-data'] = [ instance['user-data'] ]

    if 'cloud-config' not in instance:
        instance['cloud-config'] = {}
    if 'packages' not in instance['cloud-config']:
        instance['cloud-config']['packages'] = []
    if 'puppet' not in instance['cloud-config']['packages']:
        instance['cloud-config']['packages'].append('puppet')

    if isinstance(instance['puppet'], basestring):
        instance['puppet'] = [ instance['puppet'] ]

    for manifest in instance['puppet']:
        data = _load_manifest(manifest)
        instance['user-data'].append(data)

    del instance['puppet']
