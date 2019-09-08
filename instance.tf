resource "random_integer" "sg" {
  min = 0
  max = 5000
}

data "template_file" "cloud-init" {
  template = "${file("${path.module}/cloud-init.yaml")}"

  vars {
    template_zip_b64 = "${base64encode(file(local.zipfile))}"
  }

  depends_on = [
    "data.archive_file.init_dir",
  ]
}

resource "aws_security_group" "allports-exposed" {
  name        = "allports-exposed-server-sg-${random_integer.sg.result}"
  description = "This service does nothing but expose all ports to allow for enumeration"
  vpc_id      = "${var.vpc_id}"

  tags {
    Name = "allports-exposed-server-sg-${random_integer.sg.result}"
  }

  ingress = {
    cidr_blocks = [
      "0.0.0.0/0",
    ]

    protocol    = -1
    from_port   = 0
    to_port     = 0
    description = "allow all ingress allports-exposed"
  }

  egress = {
    cidr_blocks = [
      "0.0.0.0/0",
    ]

    # ALL
    protocol    = -1
    from_port   = 0
    to_port     = 0
    description = "allow all outbound"
  }
}

resource "aws_instance" "allports-host" {
  ami           = "${data.aws_ami.ubuntu.id}"
  instance_type = "t2.micro"
  user_data     = "${data.template_file.cloud-init.rendered}"

  vpc_security_group_ids = [
    "${aws_security_group.allports-exposed.id}",
  ]

  key_name  = "${var.ssh_key_name}"
  subnet_id = "${var.subnet_id}"

  tags = {
    Name = "allports-exposed-host"
  }

  depends_on = [
    "aws_security_group.allports-exposed",
  ]
}

output "ip-private" {
  value = "${aws_instance.allports-host.private_ip}"
}

output "ip-public" {
  value = "${aws_instance.allports-host.public_ip}"
}
