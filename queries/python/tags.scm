;; tags.scm for Python symbol extraction
(
 (function_definition
   name: (identifier) @name
   (#set! type "function")
  )
 (class_definition
   name: (identifier) @name
   (#set! type "class")
  )
)
