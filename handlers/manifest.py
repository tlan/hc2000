#part-handler

import boto.utils
import grp
import os
import os.path
import pwd
import re
import yaml

def _mode_x_from_r(mode):
    return mode | (mode & 0444) >> 2

def _mk_parents(data, parts):
    partial_path = ''
    for part in parts:
        partial_path += part + '/'
        try:
            os.mkdir(partial_path)
            if partial_path in data.files:
                data.files[partial_path]['mode'] = \
                    _mode_x_from_r(data.files[partial_path]['mode'])
                data.created.append(partial_path)
        except OSError:
            pass

def _get_key(data, source):
    bucket, _, key = source[len('s3://'):].partition('/')
    if data.s3 is None:
        data.s3 = boto.connect_s3()
    if bucket not in data.buckets:
        data.buckets[bucket] = boto.s3.bucket.Bucket(data.s3, bucket)
    return boto.s3.key.Key(data.buckets[bucket], key)

def _fetch_file(data, source, file):
    if source.startswith('s3://'):
        key = _get_key(data, source)
        key.get_contents_to_file(file)
    else:
        raise NotImplementedError

def _mk_file(data, path, source, content, target):
    parts = path.split('/')
    _mk_parents(data, parts[:-1])
    if not parts[-1]:
        return
    if target is not None:
        os.symlink(target, path)
    else:
        with open(path, 'w+b') as file:
            if content is not None:
                file.write(content)
            else:
                _fetch_file(data, source, file)
    data.created.append(path)

def _create(data):
    for path, attr in sorted(data.files.iteritems()):
        _mk_file(data, path, attr['source'], attr['content'], attr['target'])
    for path in reversed(data.created):
        attr = data.files[path]
        if not attr.get('target', None):
            os.chmod(path, attr['mode'])
        os.lchown(path, attr['uid'], attr['gid'])

def _uid(user):
    try: return pwd.getpwnam(user).pw_uid
    except: return -1

def _gid(group):
    try: return grp.getgrnam(group).gr_gid
    except: return -1

def _resolve_owner_group(entry):
    if 'owner' in entry:
        entry['uid'] = _uid(entry.pop('owner'))
    if 'group' in entry:
        entry['gid'] = _gid(entry.pop('group'))

def _is_absolute(path):
    return bool(re.match('((https?|s3):/)?/', path))

def _join_paths(first, second):
    if _is_absolute(second):
        return second
    if first.endswith('/'):
        return first + second
    return first + '/' + second

def _load_entry(data, mapping):
    default = {
        'destination':  '',
        'content':      None,
        'source':       '',
        'target':       None,
        'uid':          -1,
        'gid':          -1,
        'mode':         0644,
    }

    files = mapping.pop('files', [ '' ])
    _resolve_owner_group(mapping)

    default.update(mapping)

    for file in files:
        if isinstance(file, basestring):
            file = { 'filename': file }

        filename = file.pop('filename', '')
        destination = file.pop('destination', filename)
        source = file.get('source', filename)

        destination = os.path.join(default['destination'], destination)
        file['source'] = _join_paths(default['source'], source)
        _resolve_owner_group(file)

        entry = default.copy()
        entry.update(file)
        data.files[destination] = entry

def _load(data, source):
    manifest = yaml.safe_load(source)
    if isinstance(manifest, dict):
        manifest = [ manifest ]
    for entry in manifest:
        _load_entry(data, entry)

class _HC2000:
    def __init__(self):
        self.files = {}
        self.created = []

        self.s3 = None
        self.buckets = {}

def list_types():
    return [ 'text/hc2000-manifest' ]

def handle_part(data, ctype, filename, payload):
    if ctype == 'text/hc2000-manifest':
        _load(data.hc2000_manifest, payload)
    elif ctype == '__begin__':
        data.hc2000_manifest = _HC2000()
    elif ctype == '__end__':
        _create(data.hc2000_manifest)

if __name__ == '__main__':
    import sys
    class Data: pass
    data = Data()
    handle_part(data, '__begin__', None, None)
    for arg in sys.argv[1:]:
        with open(arg, 'rb') as file:
            handle_part(data, 'text/hc2000-manifest', arg, file)
    handle_part(data, '__end__', None, None)
