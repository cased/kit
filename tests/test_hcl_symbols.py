import os
import tempfile

from kit import Repository


def test_hcl_symbol_extraction():
    hcl_content = """
provider "aws" {
  region = "us-west-2"
}

resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfa1f0"
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
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        hcl_path = os.path.join(tmpdir, "main.tf")
        with open(hcl_path, "w") as f:
            f.write(hcl_content)
        repository = Repository(tmpdir)
        symbols = repository.extract_symbols("main.tf")
        types = {s["type"] for s in symbols}
        names = {s["name"] for s in symbols if "name" in s}

        # Expected symbols based on HCL query and updated extractor logic
        expected = {
            "aws",  # provider "aws"
            "aws_instance.web",  # resource "aws_instance" "web"
            "aws_s3_bucket.bucket",  # resource "aws_s3_bucket" "bucket"
            "instance_count",  # variable "instance_count"
            "instance_id",  # output "instance_id"
            "vpc",  # module "vpc"
            "locals",  # locals block
            # Note: no terraform block in this fixture
        }

        # Assert individual expected symbols exist
        for name in expected:
            assert name in names, f"Expected name {name} not found in {names}"

        # Check types for resource blocks (should be unquoted resource type)
        resource_types = {s["subtype"] for s in symbols if s["type"] == "resource" and "subtype" in s}
        assert "aws_instance" in resource_types
        assert "aws_s3_bucket" in resource_types

        # Check for provider and locals types
        assert "provider" in types
        assert "locals" in types


def test_hcl_symbol_edge_cases():
    hcl_content = """
resource "aws_security_group" "sg" {
  name        = "allow_tls"
  description = "Allow TLS inbound traffic"
}

resource "aws_lb_listener" "listener" {
  port     = 443
  protocol = "HTTPS"
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 2.0"
    }
  }
}
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        hcl_path = os.path.join(tmpdir, "main.tf")
        with open(hcl_path, "w") as f:
            f.write(hcl_content)
        repository = Repository(tmpdir)
        symbols = repository.extract_symbols("main.tf")
        types = {s["type"] for s in symbols}
        subtypes = {s["subtype"] for s in symbols if "subtype" in s}
        {s["name"] for s in symbols if "name" in s}
        # Should include the unnamed terraform block
        assert "terraform" in types or "block" in types
        # Should include specific resource subtypes (unquoted)
        assert "aws_security_group" in subtypes
        assert "aws_lb_listener" in subtypes
