import boto.iam
import hc2002.config as config

connection = None

def get_connection():
    global connection
    if connection is None:
        connection = boto.iam.connect_to_region('universal',
                aws_access_key_id=config.aws_access_key,
                aws_secret_access_key=config.aws_secret_key)
    return connection
