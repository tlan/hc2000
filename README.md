This tool aims to be a thin wrapper over AWS APIs. It's main development focus
is on deployment scenarios, and translating API calls to a declarative syntax
that can be maintained in version control. Extensions to the AWS APIs currently
focus on integration and extension of CloudInit functionality.

It is still very early in the development and some ideas are maturing. Expect
changes on a whim and the ability to influence the project's direction (until I
say no, that is :-p -- João)

For now, hc2000 exposes a mostly seamless interface to running isolated
instances, spot-priced instances, launch configurations and auto-scaling groups
with scheduled activities.

Look at the examples, the --help option and try to avoid the code for now ;-)

# Before you get started

You should have AWS ec2 and autoscale command-line tools installed and
configured when playing with hc2000. You should be familiar with EC2 and
auto-scaling groups.

Currently the tool will help you launch instances and auto-scaling groups. It
will not help you so much in bringing them down and cleaning up. You have been
warned :-p

# Getting started

## AWS Credentials

The recommended setup is to configure environment variables either containing or
pointing to the credentials you are using. The AWS region can also be configured
this way.

hc2000 will pick up the following environment variables, if available:

* AWS_ACCESS_KEY - AWS Access Key Id
* AWS_SECRET_KEY - AWS Secret Access Key corresponding to access key above
* EC2_REGION - an AWS EC2 region, examples are hard-coded for eu-west-1

For the benefit of EC2 and AutoScaling command-line tools you may additionally
want to configure these variables:

* EC2_URL - picked up by EC2 tools, the service URL that goes with the region
  (e.g., https://ec2.${EC2_REGION}.amazonaws.com)
* AWS_CREDENTIAL_FILE - used by AutoScaling tools, the location of a file
  containing your AWS Access Key Id and Secret Access Key.

The bootstrap command that will create a new Key Pair and a Security Group.
These will allow you to SSH into instances you create. The default options
should work out-of-the-box with the provided examples.

    $ ./hc2000 bootstrap

From there, look at the examples and launch instances or auto-scaling groups.
hc2000 will output the reservation or spot-instance request identifiers. You'll
be able to reference auto-scaling groups by the name specified in the instance
definition.

    $ ./hc2000 launch examples/simple-instance.yaml

Use ec2-describe-instances to find your instance and public hostname:

    $ ec2-describe-instances

If you used the bootstrap command, and are using the examples you'll be able to
SSH into the instance using:

    $ ssh -i ./identities/hc2000.pem -l ec2-user ec2-123-45-67-89.eu-west-1.compute.amazonaws.com

Replacing the hostname, above, with the one you got in the output from
ec2-describe-instances.

# Handy AWS commands

To keep your AWS account in check, when playing with hc2000, make sure to
familiarize yourself with these commands:

* ec2-describe-instances - list running instances, will include terminated
  instances for a while after termination.
* ec2-terminate-instances - use to clean up "isolated" and spot-instance
  requests
* as-describe-auto-scaling-groups - list currently configured auto-scaling
  groups
* as-set-desired-capacity - set the number of instances that should be running
  in an auto-scaling group, within the minimum and maximum bounds specified in
  the instance definition.
* as-delete-auto-scaling-group - delete an auto-scaling group, the capacity must
  be zero and no auto-scaling activities may be ongoing for this to succeed.
* as-describe-launch-config - list launch configurations that can be used by
  auto-scaling-groups.
* as-delete-launch-config - delete a launch configuration.
