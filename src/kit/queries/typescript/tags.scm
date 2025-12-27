;; tags.scm for TypeScript symbol extraction

; Function declarations
(function_declaration
  name: (identifier) @name @definition.function)

; Class declarations (with optional modifiers like export)
(class_declaration
  name: (type_identifier) @name @definition.class)

; Interface declarations
(interface_declaration
  name: (type_identifier) @name @definition.interface)

; Enum declarations
(enum_declaration
  name: (identifier) @name @definition.enum)

; Class methods
(class_body
  (method_definition
    name: (property_identifier) @name @definition.method))

; Arrow functions assigned to const/let (lexical_declaration)
(lexical_declaration
  (variable_declarator
    name: (identifier) @name
    value: (arrow_function)) @definition.function)

; Arrow functions assigned to var (variable_declaration)
(variable_declaration
  (variable_declarator
    name: (identifier) @name
    value: (arrow_function)) @definition.function)

; Regular functions assigned to const/let
(lexical_declaration
  (variable_declarator
    name: (identifier) @name
    value: (function_expression)) @definition.function)

; Regular functions assigned to var
(variable_declaration
  (variable_declarator
    name: (identifier) @name
    value: (function_expression)) @definition.function)

; Exported arrow functions (export const/let)
(export_statement
  declaration: (lexical_declaration
    (variable_declarator
      name: (identifier) @name
      value: (arrow_function)) @definition.function))

; Exported arrow functions (export var)
(export_statement
  declaration: (variable_declaration
    (variable_declarator
      name: (identifier) @name
      value: (arrow_function)) @definition.function))

; Exported function expressions (const/let)
(export_statement
  declaration: (lexical_declaration
    (variable_declarator
      name: (identifier) @name
      value: (function_expression)) @definition.function))

; Exported function expressions (var)
(export_statement
  declaration: (variable_declaration
    (variable_declarator
      name: (identifier) @name
      value: (function_expression)) @definition.function))

; Exported function declarations
(export_statement
  declaration: (function_declaration
    name: (identifier) @name @definition.function))

; Exported class declarations
(export_statement
  declaration: (class_declaration
    name: (type_identifier) @name @definition.class))

; Exported interface declarations
(export_statement
  declaration: (interface_declaration
    name: (type_identifier) @name @definition.interface))

; Exported enum declarations
(export_statement
  declaration: (enum_declaration
    name: (identifier) @name @definition.enum))

; Type alias declarations
(type_alias_declaration
  name: (type_identifier) @name @definition.type)

; Exported type alias declarations
(export_statement
  declaration: (type_alias_declaration
    name: (type_identifier) @name @definition.type))

; Namespace (internal_module)
(internal_module
  name: (identifier) @name @definition.namespace)

; Generator functions
(generator_function_declaration
  name: (identifier) @name @definition.function)

; Exported generator functions
(export_statement
  declaration: (generator_function_declaration
    name: (identifier) @name @definition.function))
