;; tags.scm for Swift symbol extraction (tree-sitter-swift)

; Function declarations
(function_declaration
  name: (simple_identifier) @name) @definition.function

; Class declarations (keyword-differentiated from struct/enum/extension)
(class_declaration
  "class"
  name: (type_identifier) @name) @definition.class

; Actor declarations
(class_declaration
  "actor"
  name: (type_identifier) @name) @definition.actor

; Struct declarations
(class_declaration
  "struct"
  name: (type_identifier) @name) @definition.struct

; Enum declarations
(class_declaration
  "enum"
  name: (type_identifier) @name) @definition.enum

; Extension declarations (name field is user_type, not type_identifier)
(class_declaration
  "extension"
  name: (user_type) @name) @definition.extension

; Protocol declarations
(protocol_declaration
  name: (type_identifier) @name) @definition.protocol

; Type alias declarations
(typealias_declaration
  name: (type_identifier) @name) @definition.typealias

; Initializer declarations
(init_declaration
  "init" @name) @definition.initializer
