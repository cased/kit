; Example tags.scm for JavaScript (tree-sitter-javascript)
; See https://github.com/tree-sitter/tree-sitter-javascript/blob/master/queries/highlights.scm for reference

(function_declaration
  name: (identifier) @function)

(class_declaration
  name: (identifier) @class)
