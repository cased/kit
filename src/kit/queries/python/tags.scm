;; tags.scm for Python symbol extraction

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
