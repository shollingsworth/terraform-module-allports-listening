# Usage

```
module "allports-host" {
  source          = "git::https://github.com/shollingsworth/terraform-module-allports-listening.git?ref=master"
  description = "Server responds on all ports (except 22)"
  instance_type = "t2.small"
  name = "all-ports-listening-server"
  profile = "aws-profile-name"
  region =  "us-west-2"
  role =  "AWS_PORTS_LISTENING"
  ssh_key_name = "jdoe"
  subnet_id =  "subnet-0000000"
  ubuntu_ami_name = ".*hvm-ssd/ubuntu-disco-19.04-amd64-server.*"
  vpc_id = "vpc-0000000"
  thread_count = 20
}
```
