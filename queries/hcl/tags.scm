; Capture resource blocks (resource "aws_instance" "example")
(block
  (identifier) @type
  (string_lit) @name
) @definition.block

; Capture variables (variable "my_var")
(block
  (identifier) @type
  (string_lit) @name
  (#eq? @type "variable")
) @definition.variable

; Capture outputs (output "my_output")
(block
  (identifier) @type
  (string_lit) @name
  (#eq? @type "output")
) @definition.output

; Capture locals (locals {})
(block
  (identifier) @type
  (#eq? @type "locals")
) @definition.locals

; Capture modules (module "my_module")
(block
  (identifier) @type
  (string_lit) @name
  (#eq? @type "module")
) @definition.module

; Capture providers (provider "aws")
(block
  (identifier) @type
  (string_lit) @name
  (#eq? @type "provider")
) @definition.provider

; Capture data sources (data "aws_ami" "example")
(block
  (identifier) @block_type
  (string_lit) @type
  (string_lit) @name
  (#eq? @block_type "data")
) @definition.data
