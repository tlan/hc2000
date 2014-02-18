import boto
import boto.exception
import json

import hc2002.aws.iam
from hc2002.validation import absolute_path, in_, one_or_more, validate, \
        validate_keys, validate_values

_role_policy = one_or_more({
    'action': one_or_more(basestring),
    'resource': one_or_more(basestring),
    'condition': dict,
})

validator = {
    'name': basestring,
    'path': absolute_path,
    'policy': [
        dict,
        validate_values([
            dict,
            validate_keys(in_('allow', 'deny')),
            validate_values(_role_policy),
        ]),
    ],
}

def _setup_iam_connection():
    global iam
    iam = hc2002.aws.iam.get_connection()

_policy_effects = { 'allow': 'Allow', 'deny': 'Deny' }

def _translate_role_policy(policy):
    policy_statements = []
    for effect, statements in policy.iteritems():
        effect = effect.capitalize()
        for s in statements:
            statement = {
                'Effect': effect,
                'Action': s['action'],
                'Resource': s['resource'],
            }
            if 'condition' in s:
                statement['Condition'] = s['condition']
            policy_statements.append(statement)
    return json.dumps({ 'Statement': policy_statements })

def _create_role(role, path='/'):
    """Creates an IAM role, if one doesn't exist with the same name.

    The path argument is only used if the role is being created, it is ignored,
    otherwise.
    """
    try:
        iam.create_role(role, path=path)
        return True
    except boto.exception.BotoServerError as err:
        if err.status != 409:
            raise

def _create_instance_profile(instance_profile, path='/', role=None):
    """Creates an IAM instance profile, if one doesn't exist with the same
    name, and associates it with an existing IAM role.

    If the profile is associated with a different role, it will be updated.

    The path argument is only used if the profile is being created, it is
    ignored, otherwise.
    """
    if role is None: role = instance_profile

    profile_roles = {}
    try:
        iam.create_instance_profile(instance_profile, path=path)
    except boto.exception.BotoServerError as err:
        if err.status != 409:
            raise

        profile_roles = iam.get_instance_profile(instance_profile) \
                ['get_instance_profile_response'] \
                ['get_instance_profile_result'] \
                ['instance_profile'] \
                ['roles']
        if 'member' in profile_roles:
            iam.remove_role_from_instance_profile(instance_profile,
                    profile_roles['member']['role_name'])

def _set_role_policy(role, policy):
    """Sets or resets policies associated with an IAM role."""
    for name, policy in policy.iteritems():
        policy = _translate_role_policy(policy)
        iam.put_role_policy(role, name, policy)

def _list_role_policies(role):
    result = { 'marker': None }
    while 'marker' in result:
        result = iam.list_role_policies(role, result['marker']) \
                ['list_role_policies_response'] \
                ['list_role_policies_result']
        for name in result['policy_names']:
            yield name

def _delete_role_policies(role):
    """Deletes all policies from an IAM role."""
    for policy_name in _list_role_policies(role):
        iam.delete_role_policy(role, policy_name)

def create(role):
    _setup_iam_connection()

    validate(validator, role)

    _create_instance_profile(role['name'], role['path'])
    _create_role(role['name'], role['path']) \
            or _delete_role_policies(role['name'])
    _set_role_policy(role['name'], role['policy'])

    # That's instance profile, role:
    iam.add_role_to_instance_profile(role['name'], role['name'])

def delete(name):
    _setup_iam_connection()

    try:
        iam.remove_role_from_instance_profile(name, name)
    except boto.exception.BotoServerError as err:
        print err.status, err.error_code
        if err.status != 404 \
                and (err.status != 400 or err.error_code != 'ValidationError'):
        # Role or instance profile don't exist
            raise

    try:
        iam.delete_instance_profile(name)
    except boto.exception.BotoServerError as err:
        # Function will fail with 409 error status if IAM instance-profile is
        # attached to an IAM role with a different name. That's intentional as
        # it is not an hc2002 role.

        print err.status, err.error_code
        if err.status != 404 \
                and (err.status != 400 or err.error_code != 'ValidationError'):
        # Instance profile doesn't exist
            raise

    try:
        _delete_role_policies(name)
        iam.delete_role(name)
    except boto.exception.BotoServerError as err:
        print err.status, err.error_code
        if err.status != 404 \
                and (err.status != 400 or err.error_code != 'ValidationError'):
        # Role doesn't exist
            raise
