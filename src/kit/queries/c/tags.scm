;; C symbol queries (tree-sitter-c)

;; Functions
(function_definition
  declarator: (function_declarator
                declarator: (identifier) @name)) @definition.function

;; Structs
(struct_specifier
  name: (type_identifier) @name) @definition.struct

;; Enums
(enum_specifier
  name: (type_identifier) @name) @definition.enum
