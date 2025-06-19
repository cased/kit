;; tags.scm for Python symbol extraction

; Import statements
(import_statement
  name: (dotted_name) @name) @definition.import

(import_statement
  name: (aliased_import
    name: (dotted_name) @name)) @definition.import

(import_from_statement
  module_name: (dotted_name) @name) @definition.import

(import_from_statement
  module_name: (relative_import
                 (dotted_name) @name)) @definition.import

; Import aliases
(aliased_import
  alias: (identifier) @name) @definition.import_alias

; Top-level function definitions (direct child of module, potentially decorated)
(module
  (decorated_definition
    definition: (function_definition
      name: (identifier) @name) @definition.function))
(module
  (function_definition
    name: (identifier) @name) @definition.function)

; Async top-level function definitions (direct child of module, potentially decorated) - AFTER general function
(module
  (decorated_definition
      definition: (function_definition
          "async"
          name: (identifier) @name) @definition.function))
(module
  (function_definition
    "async"
    name: (identifier) @name) @definition.function)

; Class definitions
(class_definition
  name: (identifier) @name) @definition.class

; Methods within classes (potentially decorated)
(class_definition
  body: (_ 
    (decorated_definition
        definition: (function_definition
            name: (identifier) @name) @definition.method)))
(class_definition
  body: (_ 
    (function_definition
      name: (identifier) @name) @definition.method
  ))

; Async methods within classes (potentially decorated) - AFTER general method
(class_definition
  body: (_ 
      (decorated_definition
          definition: (function_definition
              "async"
              name: (identifier) @name) @definition.method)))
(class_definition
  body: (_ 
    (function_definition
      "async" ; Match the async keyword
      name: (identifier) @name) @definition.method
  ))

; Function calls - capture complete call expressions with arguments and line numbers
; 
; This section captures all function and method calls in Python code.
; Each captured call includes:
; - name: The function/method name being called (e.g., "print", "join", "method")
; - type: "call" 
; - code: Complete call expression with arguments (e.g., 'print("hello")', 'os.path.join("a", "b")')
; - start_line/end_line: Exact line numbers where the call occurs
;
; Examples of what gets captured:
; - print("Hello") -> name: "print", code: 'print("Hello")'
; - obj.method(x, y) -> name: "method", code: "obj.method(x, y)"
; - os.path.join("a", "b") -> name: "join", code: 'os.path.join("a", "b")'
; - text.upper().strip() -> captures both "upper" and "strip" calls separately

; Simple function calls (e.g., print("hello"), len([1,2,3]), max(a, b, c))
(call
  function: (identifier) @name) @definition.call

; Method calls (e.g., obj.method(x, y), self.add(1, 2))
(call
  function: (attribute
    attribute: (identifier) @name)) @definition.call

; Chained method calls (e.g., obj.method1().method2(arg))
(call
  function: (attribute
    object: (call)
    attribute: (identifier) @name)) @definition.call

; Module function calls (e.g., os.path.join("a", "b"), math.sqrt(16))
(call
  function: (attribute
    object: (attribute)
    attribute: (identifier) @name)) @definition.call
