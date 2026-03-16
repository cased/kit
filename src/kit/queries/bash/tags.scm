;; tags.scm for Bash symbol extraction (tree-sitter-bash)

; Function definitions (covers both "function name()" and "name()" syntax)
(function_definition
  name: (word) @name) @definition.function
