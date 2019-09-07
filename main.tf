provider "aws" {
  profile = "${var.profile}"
  region  = "${var.region}"
}

data "aws_ami" "ubuntu" {
  # Canonical/Ubuntu
  owners      = ["099720109477"]
  most_recent = true
  name_regex  = "${var.ubuntu_ami_name}"

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

output "ami-id" {
  value = "${data.aws_ami.ubuntu.id}"
}
