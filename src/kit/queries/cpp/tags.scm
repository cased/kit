;; C++ symbol queries (tree-sitter-cpp)

;; Classes
(class_specifier
  name: (type_identifier) @name) @definition.class

;; Structs
(struct_specifier
  name: (type_identifier) @name) @definition.struct

;; Enums
(enum_specifier
  name: (type_identifier) @name) @definition.enum

;; Functions  
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @name)) @definition.function 