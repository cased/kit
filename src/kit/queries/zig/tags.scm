;; tags.scm for Zig symbol extraction

; Function declarations with bodies
((Decl
  (FnProto
    function: (IDENTIFIER) @name)
  (Block)) @definition.function)

; Struct declarations via const bindings
(VarDecl
  (IDENTIFIER) @name
  (ErrorUnionExpr
    (SuffixExpr
      (ContainerDecl
        (ContainerDeclType) @container_kind
        (#match? @container_kind "^struct")
      ) @definition.struct)))

; Enum declarations via const bindings
(VarDecl
  (IDENTIFIER) @name
  (ErrorUnionExpr
    (SuffixExpr
      (ContainerDecl
        (ContainerDeclType) @container_kind
        (#match? @container_kind "^enum")
      ) @definition.enum)))

; Union declarations via const bindings
(VarDecl
  (IDENTIFIER) @name
  (ErrorUnionExpr
    (SuffixExpr
      (ContainerDecl
        (ContainerDeclType) @container_kind
        (#match? @container_kind "^union")
      ) @definition.union)))
