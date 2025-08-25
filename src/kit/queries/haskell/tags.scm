;; Haskell symbol queries (tree-sitter-haskell)
;; Based on node/field names from the grammar's highlights.scm.

; ---------------------------------------------------------------------------
; Modules
; Example: module My.Module where
(module
  (module_id) @name) @definition.module

; ---------------------------------------------------------------------------
; Functions
; Named function declaration:  foo x y = ...
(decl/function
  name: (variable) @name) @definition.function

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
; Note: Type-level declarations (data/newtype/type/class) are grammar-version specific.
; Their exact node names are not shown in highlights.scm, so they are omitted here
; to avoid query compile errors. Once confirmed (e.g., via node-types.json), add patterns like:
; (decl/data (name) @name) @definition.data
; (decl/newtype (name) @name) @definition.newtype
; (decl/type (name) @name) @definition.type
; (decl/class (name) @name) @definition.class
