;; Kotlin symbol queries (tree-sitter-kotlin)

;; Classes
(class_declaration
  (type_identifier) @name) @definition.class

;; Objects
(object_declaration
  (type_identifier) @name) @definition.object

;; Functions
(function_declaration
  (simple_identifier) @name) @definition.function 