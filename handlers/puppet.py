def list_types():
    return [ 'text/puppet' ]

def _handle_mime_begin(data, filename, payload):
    data.part_handlers['text/cloud-config'](data, 'text/cloud-config', 'hc2000-puppet-install',
            '\n'.join([ '#cloud-config', 'packages: [ puppet ]', '' ]))

def _handle_mime_puppet(data, filename, payload):
    data.part_handlers['text/x-shellscript'](data, 'text/x-shellscript', filename, '#!/usr/bin/puppet apply\n' + payload)

_handlers = {
    '__begin__': _handle_mime_begin,
    'text/puppet': _handle_mime_puppet,
}

def handle_part(data, ctype, filename, payload):
    if ctype in _handlers:
        _handlers[ctype](data, filename, payload)
