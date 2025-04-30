;; tags.scm for Go symbol extraction (tree-sitter-go)

; Function Declarations (including main)
(function_declaration
  name: (identifier) @name) @definition.function

; Method Declarations (functions with receivers)
(method_declaration
    name: (field_identifier) @name) @definition.method

; Struct Type Declarations
(type_declaration
    (type_spec
        name: (type_identifier) @name
        type: (struct_type)) @definition.struct)

; Interface Type Declarations
(type_declaration
    (type_spec
        name: (type_identifier) @name
        type: (interface_type)) @definition.interface)

; Package-level variable declarations
(var_declaration
    (var_spec
        name: (identifier) @name)) @definition.variable

; Package-level constant declarations
(const_declaration
    (const_spec
        name: (identifier) @name)) @definition.constant
