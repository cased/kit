;; tags.scm for TOML symbol extraction (tree-sitter-toml)

; Table headers with bare key: [section]
(table (bare_key) @name) @definition.table

; Table headers with dotted key: [section.subsection]
(table (dotted_key) @name) @definition.table

; Table headers with quoted key: ["section.name"]
(table (quoted_key) @name) @definition.table

; Array table headers with bare key: [[array]]
(table_array_element (bare_key) @name) @definition.table_array

; Array table headers with dotted key: [[parent.array]]
(table_array_element (dotted_key) @name) @definition.table_array

; Array table headers with quoted key: [["array.name"]]
(table_array_element (quoted_key) @name) @definition.table_array
