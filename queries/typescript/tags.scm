;; tags.scm for TypeScript symbol extraction

; functions
(function_declaration
  name: (identifier) @name
  (#set! type "function")
)

; classes (with optional modifiers like export)
(class_declaration
  name: (type_identifier) @name
  (#set! type "class")
)

; interfaces
(interface_declaration
  name: (type_identifier) @name
  (#set! type "interface")
)

; enums
(enum_declaration
  name: (identifier) @name
  (#set! type "enum")
)

; methods inside classes or object types
(method_signature
  name: (property_identifier) @name
  (#set! type "method")
)

; class methods (actual implementations)
(method_definition
  name: (property_identifier) @name
  (#set! type "method")
)
