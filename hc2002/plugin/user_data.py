import hc2002.plugin as plugin
import os.path
import email.mime.base
import email.mime.multipart
import email.mime.text

plugin.register_for_resource(__name__, 'hc2002.resource.instance')

_magic_to_mime = {
    '#!':               ('text', 'x-shellscript'),
    '#cloud-boothook':  ('text', 'cloud-boothook'),
    '#cloud-config':    ('text', 'cloud-config'),
    '#include':         ('text', 'x-include-url'),
    '#part-handler':    ('text', 'part-handler'),
    '#upstart-job':     ('text', 'upstart-job'),

    # TODO: This plugin should not know about file manifests, maybe?
    '#manifest':        ('text', 'hc2000-manifest'),
}

def _read_file(filename):
    with open(filename, 'rb') as f:
        filename = os.path.basename(filename)
        return f.read(), filename

def _process_entry(entry, filename=None):
    if entry.startswith('file:'):
        entry, filename = _read_file(entry[5:])

    maintype, subtype = ('application', 'octet-stream')
    for magic, mime in _magic_to_mime.iteritems():
        if entry.startswith(magic):
            maintype, subtype = mime
            break

    if maintype == 'text':
        msg = email.mime.text.MIMEText(entry, subtype)
    else:
        msg = email.mime.base.MIMEBase(maintype, subtype)
        msg.set_payload(entry)

    if filename:
        msg.add_header('Content-Disposition', 'attachment', filename=filename)
    else:
        msg.add_header('Content-Disposition', 'attachment')

    return msg

def apply(instance):
    if 'user-data' not in instance \
            or not isinstance(instance['user-data'], list):
        return

    data = email.mime.multipart.MIMEMultipart()
    for entry in instance['user-data']:
        data.attach(_process_entry(entry))

    # Replace user-data with MIME-ified version.
    instance['user-data'] = data.as_string()
