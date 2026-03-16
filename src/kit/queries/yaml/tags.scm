;; tags.scm for YAML symbol extraction (tree-sitter-yaml)
;; Only captures top-level mapping keys (direct children of document root).
;; Use the full mapping pair as the definition so symbol spans/code include values.

(stream
  (document
    (block_node
      (block_mapping
        (block_mapping_pair
          key: (flow_node (_) @name)) @definition.key))))
