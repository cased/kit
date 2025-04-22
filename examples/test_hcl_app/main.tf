# Example Terraform configuration for AWS

provider "aws" {
  region = "us-west-2"
}

resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"
  tags = {
    Name = "WebServer"
  }
}

resource "aws_s3_bucket" "bucket" {
  bucket = "my-example-bucket-123456"
  acl    = "private"
}

variable "instance_count" {
  description = "Number of EC2 instances to launch"
  type        = number
  default     = 2
}

output "instance_id" {
  value = aws_instance.web.id
}

locals {
  environment = "dev"
  owner       = "test-user"
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  name   = "example-vpc"
  cidr   = "10.0.0.0/16"
}
