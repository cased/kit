;; C# symbol queries (tree-sitter-c-sharp)

;; Classes
(class_declaration
  name: (identifier) @name) @definition.class

;; Structs
(struct_declaration
  name: (identifier) @name) @definition.struct

;; Records (C# 9+)
(record_declaration
  name: (identifier) @name) @definition.record

;; Interfaces
(interface_declaration
  name: (identifier) @name) @definition.interface

;; Enums
(enum_declaration
  name: (identifier) @name) @definition.enum

;; Delegates
(delegate_declaration
  name: (identifier) @name) @definition.delegate

;; Methods
(method_declaration
  name: (identifier) @name) @definition.method

;; Constructors
(constructor_declaration
  name: (identifier) @name) @definition.constructor

;; Properties
(property_declaration
  name: (identifier) @name) @definition.property

;; Namespaces
(namespace_declaration
  name: (identifier) @name) @definition.namespace

;; Namespaces with qualified names (e.g., namespace Foo.Bar)
(namespace_declaration
  name: (qualified_name) @name) @definition.namespace
