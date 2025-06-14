;; tags.scm for Dart symbol extraction

; Class declarations
(class_definition
  name: (identifier) @name) @definition.class

; Function declarations
(function_signature
  name: (identifier) @name) @definition.function

; Mixin declarations
(mixin_declaration
  name: (identifier) @name) @definition.mixin

; Enum declarations
(enum_declaration
  name: (identifier) @name) @definition.enum

; Extension declarations
(extension_declaration
  name: (identifier) @name) @definition.extension

; Constructor declarations
(constructor_signature
  name: (identifier) @name) @definition.constructor

; Getter declarations
(getter_signature
  name: (identifier) @name) @definition.getter

; Setter declarations
(setter_signature
  name: (identifier) @name) @definition.setter

; Variable declarations
(initialized_variable_definition
  name: (identifier) @name) @definition.variable

; TODO: Add proper constant declarations pattern
; The tree-sitter-dart grammar needs to be researched for correct node types
; for const variable declarations 