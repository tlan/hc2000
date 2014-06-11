import base64
import email.utils
import grp
import hashlib
import hmac
import json
import logging
import os
import os.path
import pwd
import re
import urllib
import urllib2
import yaml

# Setup the logger
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


def _get_aws_metadata(path, timeout=10):
    md_url = "http://169.254.169.254/latest/meta-data/"
    response = urllib2.urlopen(md_url + path, timeout)
    return response.read()

def _get_s3_endpoint():
    """Returns correct s3 url based upon where the instance is located"""
    try:
        availability_zone = _get_aws_metadata("placement/availability-zone")
    except:
        # Default to eu-west-1
        return 'http://s3-eu-west-1.amazonaws.com'
    if availability_zone.startswith("us-east-1"):
        return 'http://s3.amazonaws.com'
    region = availability_zone[0:9]
    return 'http://s3-%s.amazonaws.com' % region


class S3Connection:
    """Connection to S3"""
    def __init__(self, access_key=None, secret_key=None, security_token=None):
        self.endpoint = _get_s3_endpoint()
        self.access_key = access_key
        self.secret_key = secret_key
        self.security_token = security_token

    def request(self, bucket, path, query=None):
        headers = { 'Host': bucket }
        self._authenticate_request(bucket, path, headers)
        url = self.endpoint + path + (query or '')
        LOG.info("S3 Request: %s (headers: %s)", url, headers)
        request = urllib2.Request(url, headers=headers)
        response = urllib2.urlopen(request)
        if response.getcode() == 200:
            return response

        raise RuntimeError('%s: %s' % (response.getcode(), response.read()))

    def _authenticate_request(self, bucket, path, headers):
        # See http://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html
        # Shortcuts taken liberally, this is not a full implementation.

        if not self.access_key:
            return

        date = email.utils.formatdate()
        headers['Date'] = date

        message = 'GET\n\n\n' + date + '\n'
        if self.security_token:
            headers['x-amz-security-token'] = self.security_token
            message += 'x-amz-security-token:' + self.security_token + '\n'
        message += '/' + bucket + path

        h = hmac.new(self.secret_key, message, hashlib.sha1)
        signature = base64.b64encode(h.digest())

        headers['Authorization'] = 'AWS %s:%s' % (self.access_key, signature)

class S3Object:
    """Simple representation of an object found in S3"""
    def __init__(self, md5hash, filestream):
        self.md5hash = md5hash
        self.filestream = filestream

    def get_contents_to_file(self, output_fp):
        """Write the contents of the s3 object to local file"""
        LOG.info("Writing %s to local file %s.", self.filestream.url, output_fp.name)
        for data in iter(lambda: self.filestream.read(32768), ""):
            output_fp.write(data)

class S3Bucket:
    """A read-only, view over a flat directory in AWS S3."""

    def __init__(self, s3connection, bucket, prefix=''):
        self.s3 = s3connection
        self.bucket = bucket
        self.prefix = prefix + '/'

    def get_object(self, name):
        """Read object from S3.

        Returns a S3Object
        """
        path = urllib.quote_plus(self.prefix + name, '/')
        response = self.s3.request(self.bucket, path)

        return S3Object(response.headers['ETag'][1:-1], response)


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
        md_url = 'iam/security-credentials'

        role = _get_aws_metadata(md_url)
        creds = yaml.safe_load(_get_aws_metadata(md_url + '/' + role))

        data.s3 = S3Connection(
                creds["AccessKeyId"],
                creds["SecretAccessKey"],
                creds["Token"])

    if bucket not in data.buckets:
        data.buckets[bucket] = S3Bucket(data.s3, bucket)
    return data.buckets[bucket].get_object(key)

def _fetch_file(data, source, file):
    if source.startswith('s3://'):
        LOG.info("Fetching from S3: %s", source)
        key = _get_key(data, source)
        key.get_contents_to_file(file)
    else:
        LOG.error("URI scheme not implemented while fetching %s", source)
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
    if not second:
        return first
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

        destination = _join_paths(default['destination'], destination)
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
