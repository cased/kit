import os
import tempfile
import pytest
from kit.repo import Repo
from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

def test_hcl_symbol_extraction():
    hcl_content = '''
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
'''
    with tempfile.TemporaryDirectory() as tmpdir:
        hcl_path = os.path.join(tmpdir, "main.tf")
        with open(hcl_path, "w") as f:
            f.write(hcl_content)
        repo = Repo(tmpdir)
        symbols = repo.extract_symbols("main.tf")
        types = {s["type"] for s in symbols}
        names = {s["name"] for s in symbols if "name" in s}
        assert "provider" in types
        assert "variable" in types
        assert "output" in types
        assert "locals" in types
        assert "module" in types
        assert "web" in names
        assert "bucket" in names
        assert "instance_count" in names
        assert "instance_id" in names
        assert "vpc" in names
        # Check specific resource types (parser includes quotes)
        assert '"aws_instance"' in types
        assert '"aws_s3_bucket"' in types

def test_hcl_symbol_edge_cases():
    hcl_content = '''
    # block with no name
    terraform {
      required_version = ">= 0.12"
    }

    # nested block
    resource "aws_security_group" "sg" {
      ingress {
        from_port = 80
        to_port   = 80
      }
    }

    # block with multiple string_lit children
    resource "aws_lb_listener" "listener" {
      port     = 443
      protocol = "HTTPS"
      default_action {
        type             = "forward"
        target_group_arn = "arn:aws:..."
      }
    }
    '''
    with tempfile.TemporaryDirectory() as tmpdir:
        hcl_path = os.path.join(tmpdir, "main.tf")
        with open(hcl_path, "w") as f:
            f.write(hcl_content)
        repo = Repo(tmpdir)
        symbols = repo.extract_symbols("main.tf")
        types = {s["type"] for s in symbols}
        names = {s["name"] for s in symbols if "name" in s}
        # Should include the unnamed terraform block
        assert "terraform" in types or "block" in types
        # Should include specific resource types (parser includes quotes)
        assert '"aws_security_group"' in types
        assert '"aws_lb_listener"' in types
        # Should include both resource names
        assert "sg" in names
        assert "listener" in names
