;; tags.scm for Rust symbol extraction

(function_item
  name: (identifier) @name
  (#set! type "function"))

(struct_item
  name: (type_identifier) @name
  (#set! type "struct"))

(enum_item
  name: (type_identifier) @name
  (#set! type "enum"))

(trait_item
  name: (type_identifier) @name
  (#set! type "trait"))

(impl_item
  type: (type_identifier) @name
  (#set! type "impl"))
