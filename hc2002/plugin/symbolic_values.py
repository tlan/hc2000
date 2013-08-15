import hc2002.plugin as plugin

plugin.register_for_resource(__name__, 'hc2002.resource.instance')

_prefixes = ('availability-zone:', 'image:', 'kernel:', 'key:',
        'load-balancers:', 'ramdisk:', 'security-groups:', 'spot-price:',
        'subnet:')

def apply(instance):
    def _resolve_symbol(value):
        visited = set()
        while isinstance(value, basestring) \
                and value.startswith(prefix):
            value = value.format(region=config.region, **instance)
            if value in instance \
                    and value not in visited:
                visited.add(value)
                value = instance[value]
        return value

    # Resolve symbols
    for prefix in _prefixes:
        key = prefix[:-1]
        if key not in instance:
            continue

        if isinstance(instance[key], basestring):
            instance[key] = _resolve_symbol(instance[key])
        elif isinstance(instance[key], list):
            instance[key] = map(_resolve_symbol, instance[key])

    # Drop resolvable symbols
    for key in instance.keys():
        if key.startswith(_prefixes):
            del instance[key]
