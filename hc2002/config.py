import os

region = os.environ.get('AWS_DEFAULT_REGION') \
        or os.environ.get('EC2_REGION')
aws_access_key = os.environ.get('AWS_ACCESS_KEY')
aws_secret_key = os.environ.get('AWS_SECRET_KEY')

handler_path = os.path.join(os.path.dirname(__file__), 'handler')

puppet_path = []
