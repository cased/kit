# kit Cookbook

A collection of practical recipes and code snippets for using the `kit` code intelligence toolkit. Copy, adapt, and share.

---

## 1. List All File Paths in the Repo
```python
from kit import Repo
repo = Repo(".")
for node in repo.get_file_tree():
    if not node.get("is_dir", False):
        print(node.get("path", ""))
```

## 2. List All Python Files Larger Than 1KB
```python
for node in repo.get_file_tree():
    if node.get("path", "").endswith(".py") and node.get("size", 0) > 1024:
        print(node.get("path", ""))
```

## 3. Print All Function Names in the Repo
```python
for syms in repo.index().get("symbols", {}).values():
    for sym in syms:
        if sym.get("type") == "function":
            print(sym.get("name", ""))
```

## 4. Find All Usages of a Symbol
```python
for usage in repo.find_symbol_usages("foo", symbol_type="function"):
    print(usage)
```

## 5. Export the File Tree as Markdown
```python
tree = repo.get_file_tree()
for node in sorted(tree, key=lambda x: x.get('path', '')):
    indent = "  " * node.get('path', '').count("/")
    print(f"{indent}- {node.get('name', '')}")
```

## 6. Semantic Search for a Concept
```python
results = repo.search_semantic("authentication", top_k=3, embed_fn=your_embed_fn)
for res in results:
    print(res.get("file", ""), res.get("context", ""))
```

## 7. Extract All TODO Comments
```python
todos = repo.search_text("TODO")
for todo in todos:
    content = todo.get('line_content') or todo.get('line') or ''
    print(f"{todo.get('file', '')}:{todo.get('line_number', '')}: {content}")
```

## 8. Get Context Around a Specific Line
```python
context = repo.extract_context_around_line("src/kit/repo.py", 42)
print(context)
```

## 9. Chunk a File by Symbols
```python
for chunk in repo.chunk_file_by_symbols("src/kit/repo.py"):
    print(chunk)
```

## 10. Chunk a File by Lines
```python
for chunk in repo.chunk_file_by_lines("src/kit/repo.py", max_lines=20):
    print(chunk)
```

## 11. Write the Full Index to JSON
```python
repo.write_index("repo_index.json")
```

## 12. Write All Symbols to JSON
```python
repo.write_symbols("symbols.json")
```

## 13. Write the File Tree to JSON
```python
repo.write_file_tree("file_tree.json")
```

## 14. Write All Usages of a Symbol to JSON
```python
repo.write_symbol_usages("foo", "usages.json", symbol_type="function")
```

## 15. List All Classes in the Repo
```python
for syms in repo.index().get("symbols", {}).values():
    for sym in syms:
        if sym.get("type") == "class":
            print(sym.get("name", ""))
```

## 16. Print All Files Containing a Given Word
```python
hits = repo.search_text("import os")
for hit in hits:
    print(hit.get("file", ""))
```

## 17. Find All Resource Names in HCL/Terraform
```python
for syms in repo.index().get("symbols", {}).values():
    for sym in syms:
        if sym.get("type") == "resource":
            print(sym.get("name", ""))
```

## 18. Generate a Call Graph (Basic Example)
```python
calls = {}
for syms in repo.index().get("symbols", {}).values():
    for sym in syms:
        if sym.get("type") == "function":
            usages = repo.find_symbol_usages(sym.get("name", ""), symbol_type="function")
            calls[sym.get("name", "")] = [u.get("file", "") for u in usages]
print(calls)
```

## 19. Print All Interfaces in TypeScript
```python
for syms in repo.index().get("symbols", {}).values():
    for sym in syms:
        if sym.get("type") == "interface":
            print(sym.get("name", ""))
```

## 20. List All Files in a Subdirectory
```python
for node in repo.get_file_tree():
    if node.get("path", "").startswith("src/") and not node.get("is_dir", False):
        print(node.get("path", ""))
```

---

Want to add your own recipe? Open a PR or issue!
