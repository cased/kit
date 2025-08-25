;; Haskell symbol queries (tree-sitter-haskell)
;; Based on node/field names from the grammar's highlights.scm.

; ---------------------------------------------------------------------------
; Modules (header only, avoid imports)
; Example: module My.Module where
(haskell
  (header
    (module) @name) @definition.module)

; ---------------------------------------------------------------------------
; Functions
; Named function declaration:  foo x y = ...
(decl/function
  name: (variable) @name) @definition.function

; Operator-named function declaration:  (>>=) x y = ...
(decl/function
  name: (prefix_id (operator) @name)) @definition.function

; Pattern binding that defines a function via a lambda:  foo = \x -> ...
(decl/bind
  name: (variable) @name
  (match
    expression: (expression/lambda))) @definition.function

; Optional: treat `main` as a function even if not a lambda (e.g. main = undefined)
(decl/bind
  name: (variable) @name
  (#eq? @name "main")) @definition.function

; ---------------------------------------------------------------------------
; Type-level declarations (from node-types.json)
; Data type: data T a b = ...
(data_type
  name: (name) @name) @definition.data

; Newtype: newtype T a = ...
(newtype
  name: (name) @name) @definition.newtype

; Type alias (note: grammar uses 'type_synomym')
(type_synomym
  name: (name) @name) @definition.type

; Type class: class C a where ...
(class
  name: (name) @name) @definition.class

; Type family: type family F a = ...
(type_family
  name: (name) @name) @definition.type_family

; Instance: instance C T where ... (captures the class name)
(instance
  name: (name) @name) @definition.instance
