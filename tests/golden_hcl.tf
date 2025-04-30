# Basic HCL constructs for symbol extraction testing

provider "aws" {
  region = "us-west-2"
}

resource "aws_instance" "web_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  tags = {
    Name = "HelloWorld"
  }
}

resource "aws_s3_bucket" "data_bucket" {
  bucket = "my-tf-test-bucket"
}

data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }

  owners = ["099720109477"] # Canonical
}

variable "server_port" {
  description = "The port the server will use"
  type        = number
  default     = 8080
}

output "instance_ip_addr" {
  value = aws_instance.web_server.public_ip
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "3.14.0"
}

locals {
  service_name = "my-app"
  owner        = "user@example.com"
}

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}
