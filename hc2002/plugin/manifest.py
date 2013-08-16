import hc2002.config as config
import hc2002.manifest
import hc2002.plugin as plugin
from hc2002.validation import validate
import os.path
import yaml

plugin.register_for_resource(__name__, 'hc2002.resource.instance')

def _add_handler(instance):
    filename = os.path.join(config.handler_path, 'manifest.py')
    with open(filename, 'rb') as f:
        handler = f.read()
    if not handler.startswith('#part-handler'):
        handler = '#part-handler\n' + handler
    instance['user-data'].append(handler)

def _process_manifest_tag(instance):
    if 'manifest' not in instance:
        return

    if 'user-data' not in instance:
        instance['user-data'] = []
    if isinstance(instance['user-data'], basestring):
        instance['user-data'] = [ instance['user-data'] ]

    _add_handler(instance)

    manifest = instance['manifest']
    if not isinstance(manifest, basestring):
        manifest = yaml.dump(manifest)
    if not manifest.startswith(('file:', '#manifest\n')):
        manifest = '#manifest\n' + manifest

    instance['user-data'].append(manifest)

    del instance['manifest']

def _validate_manifests(instance):
    if 'user-data' not in instance:
        return

    if isinstance(instance['user-data'], basestring):
        instance['user-data'] = [ instance['user-data'] ]

    for i, entry in enumerate(instance['user-data']):
        if not isinstance(entry, basestring):
            continue
        scope = 'user-data[%i]' % i

        #FIXME: Should either move file inlining earlier or validation
        #       later. Should NOT read the file twice. Live as plugin of a
        #       user-data plugin? :-)
        if entry.startswith('file:'):
            scope += ':%s:' % entry[5:]
            entry = open(entry[5:], 'rb').read()

        if entry.startswith('#manifest\n'):
            print "Validating manifest:\n", entry
            validate(hc2002.manifest, yaml.safe_load(entry), scope)

def apply(instance):
    _process_manifest_tag(instance)
    _validate_manifests(instance)
