variable "description" {}
variable "instance_type" {}
variable "name" {}
variable "profile" {}
variable "region" {}
variable "role" {}
variable "ssh_key_name" {}
variable "subnet_id" {}
variable "ubuntu_ami_name" {}
variable "vpc_id" {}

variable "thread_count" {
  description = "Number of threads the server should launch"
  default     = "10"
}
