# Tutorial: Automated Documentation Generation with kit

## Overview

This tutorial walks you through building an automated documentation generator for your codebase using the `kit` library. You'll learn how to extract symbols from your code and output Markdown documentation summarizing the structure of your project.

---

## Prerequisites

- Python 3.8+
- `kit` installed (e.g., `uv pip install -e .` in your repo)
- A codebase you want to document

---

## Step 1: Generate Documentation from Code Symbols

The core of this tool is extracting symbols (functions, classes, etc.) from your codebase and formatting them as Markdown.

```python
from kit import Repo

def generate_docs(repo_path: str) -> str:
    repo = Repo(repo_path)
    index = repo.index()
    lines = [f"# Documentation for {repo_path}\n"]
    for file, symbols in index["symbols"].items():
        lines.append(f"## {file}")
        for symbol in symbols:
            lines.append(f"- **{symbol['type']}** `{symbol['name']}`")
        lines.append("")
    return "\n".join(lines)
```

---

## Step 2: Command-Line Interface

Provide a CLI so users can specify the repo and output file:

```python
import argparse

def main() -> None:
    parser = argparse.ArgumentParser(description="Automated documentation generator using kit.")
    parser.add_argument("--repo", required=True, help="Path to the code repository")
    parser.add_argument("--output", help="Output Markdown file (default: stdout)")
    args = parser.parse_args()
    docs = generate_docs(args.repo)
    if args.output:
        with open(args.output, "w") as f:
            f.write(docs)
        print(f"Documentation written to {args.output}")
    else:
        print(docs)

if __name__ == "__main__":
    main()
```

---

## Step 3: Running the Tool

You can run the script like this:

```sh
python automated_doc_gen.py --repo /path/to/repo --output docs.md
```

This will generate a Markdown file listing all files and their extracted symbols.

---

## Example Output

```
# Documentation for /path/to/repo

## main.py
- **function** `main`
- **class** `MyClass`

## utils.py
- **function** `helper`
```

---

## Extending the Generator

- Add docstring extraction for richer documentation.
- Group symbols by type (functions, classes, etc).
- Output in other formats (HTML, reStructuredText).
- Integrate with CI to keep docs up to date automatically.

---

## Conclusion

With just a few lines of code, you can automate documentation for any codebase using `kit`. This approach scales to large projects and can be customized for your team's needs.
