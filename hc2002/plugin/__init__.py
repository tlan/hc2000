import importlib

def _resolve(resource):
    if isinstance(resource, basestring):
        return importlib.import_module(resource)
    return resource

def register_for_resource(plugin, resource):
    resource = _resolve(resource)

    # TODO: There isn't really a need for plugin lists to live in the resource
    # namespace, they could be maintained in this module.
    if not hasattr(resource, 'plugins'):
        resource.plugins = []
    resource.plugins.insert(0, plugin)

def apply_for_resource(resource, data):
    resource = _resolve(resource)

    if not hasattr(resource, 'plugins'):
        return

    for plugin in resource.plugins:
        plugin = _resolve(plugin)

        if not hasattr(plugin, 'apply'):
            continue

        plugin.apply(data)
