import hc2002.aws.elb

def _setup_elb_connection():
    global elb
    elb = hc2002.aws.elb.get_connection()

def list(names=None):
    _setup_elb_connection()

    return elb.get_all_load_balancers(names)
