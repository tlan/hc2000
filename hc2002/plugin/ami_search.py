import hc2002.aws.ec2
import hc2002.config as config
import hc2002.plugin as plugin
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

plugin.register_for_resource(__name__, 'hc2002.resource.instance')

class ImageNotFound(Exception):
    pass

def apply(instance):
    if not 'image' in instance \
            or not isinstance(instance['image'], dict):
        return

    search_criteria = instance['image'].copy()
    owners = search_criteria.pop('owner', None)
    executable_by = search_criteria.pop('executable-by', None)
    filters = search_criteria or None

    logger.debug("AMI search criteria: owners=%s, executable-by=%s, filters=%s"
            % (owners, executable_by, filters))

    ec2 = hc2002.aws.ec2.get_connection()
    images = ec2.get_all_images(owners=owners, executable_by=executable_by, filters=filters)

    if not images:
        raise ImageNotFound("No image found for the criteria provided: %s"
                % instance['image'])

    images = sorted(images, key=lambda x: x.name, reverse=True)
    logger.debug("Candidate AMIs (sorted): %s" % ([ i.name for i in images ]))

    instance['image'] = images[0].id
