# Tutorial: Dumping a Repo Map as JSON with kit

## Overview

This tutorial explains how to use `kit` to dump a complete map of your repository—including the file tree and all extracted symbols—as a JSON file. This is useful for further analysis, visualization, or integration with other tools.

---

## Prerequisites

- Python 3.8+
- `kit` installed
- A codebase to analyze

---

## Step 1: Dump the Repo Map

Use the `RepoMapper` class to extract the full repository map:

```python
from kit import RepoMapper
import json

repo_path = "/path/to/repo"
mapper = RepoMapper(repo_path)
repo_map = mapper.get_repo_map()
print(json.dumps(repo_map, indent=2))
```

---

## Step 2: Command-Line Usage

You can run the script as follows:

```sh
python dump_repo_map.py /path/to/repo > repo_map.json
```

This will output a JSON file containing the structure and symbols of your codebase.

---

## Example JSON Output

```json
{
  "file_tree": ["main.py", "utils.py", "models/", "models/model.py"],
  "symbols": {
    "main.py": [
      {"type": "function", "name": "main"},
      {"type": "class", "name": "App"}
    ],
    "utils.py": [
      {"type": "function", "name": "helper"}
    ]
  }
}
```

---

## Integration Ideas

- Use the JSON output to feed custom dashboards or documentation tools.
- Integrate with code search or visualization tools.
- Use for code audits, onboarding, or automated reporting.

---

## Conclusion

With just a single command, you can export a structured map of your repository for any downstream use case. This makes it easy to build custom tools and workflows on top of your codebase.
