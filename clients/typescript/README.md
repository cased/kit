# Kit TypeScript Client

TypeScript/Node.js wrapper for the Cased **Kit** CLI. This library lets you call Kit’s powerful code-analysis features from JavaScript or TypeScript with first-class typings.

## Installation

```bash
# 1) Install the TypeScript wrapper
npm install @runcased/kit              # or pnpm add / yarn add

# 2) Install the Kit CLI itself (Python)
uv pip install cased-kit               # or pipx install cased-kit; or any other python way
```

> The TS wrapper shells out to the `kit` executable, so the Python package must be on **$PATH** in the same environment where Node runs (local dev, Docker image, CI runner, etc.).

**Requirements**

- Node 16 or newer
- Python 3.10+ with `cased-kit` installed

## Quick Start

```typescript
import { Kit } from "@runcased/kit";

const kit = new Kit(); // uses `kit` from $PATH
const repo = kit.repository("./"); // current repo

(async () => {
  const info = await repo.gitInfo();
  console.log(info);

  const files = await repo.fileTree(); // structured file list
  console.log(`Repo has ${files.length} entries`);
})();
```

## Wrapper Highlights

- **Type-safe** – full `.d.ts` bundled, generics for options & results.
- **Same API shape as Python** – methods map 1-to-1 to CLI commands.
- **Repository helper** – `kit.repository(path)` returns convenience wrapper so you don’t repeat the path/ref.
- **No native deps** – only uses Node’s `child_process` to invoke CLI.

The remainder of this README contains advanced usage & API reference.

### Basic Setup

```typescript
import { Kit } from "@runcased/kit";

const kit = new Kit({
  kitPath: "kit", // Path to kit executable (optional)
  cwd: process.cwd(), // Working directory (optional)
});
```

### Repository Operations

```typescript
// Create a repository instance
const repo = kit.repository("/path/to/repo");

// Get file tree
const files = await repo.fileTree();

// Extract symbols from a file
const symbols = await repo.symbols("src/main.ts");

// Search for code
const results = await repo.search("function authenticate");

// Find symbol usages
const usages = await repo.usages("authenticate");

// Get dependencies
const deps = await repo.dependencies("src/main.ts");
```

### Semantic Search

```typescript
// Perform semantic search
const results = await repo.searchSemantic("authentication logic", {
  topK: 10,
  embeddingModel: "all-MiniLM-L6-v2",
  chunkBy: "symbols",
  buildIndex: true, // Build index on first run
});

// Results include score and content
results.forEach((result) => {
  console.log(`${result.file} (score: ${result.score})`);
  console.log(result.content);
});
```

### PR Review

```typescript
// Review a pull request
const review = await kit.reviewPR("https://github.com/owner/repo/pull/123", {
  githubToken: process.env.GITHUB_TOKEN,
  llmProvider: "anthropic",
  model: "claude-4-sonnet",
  apiKey: process.env.ANTHROPIC_API_KEY,
  priorities: ["high", "medium"],
  postAsComment: false, // Don't post to GitHub
});

console.log(review);
```

### Working with Git References

```typescript
// Work with a specific branch/tag/commit
const repo = kit.repository("/path/to/repo", "feature-branch");

// All operations will use this ref
const symbols = await repo.symbols("main.py");
const tree = await repo.fileTree();
```

### Error Handling

```typescript
import { KitError } from "@runcased/kit";

try {
  const symbols = await repo.symbols("nonexistent.ts");
} catch (error) {
  if (error instanceof Error && "code" in error) {
    const kitError = error as KitError;
    console.error(`Kit error: ${kitError.message}`);
    console.error(`Exit code: ${kitError.exitCode}`);
    console.error(`Stderr: ${kitError.stderr}`);
  }
}
```

## API Reference

### `Kit` Class

Main class for interacting with the Kit CLI.

#### Constructor

```typescript
new Kit(options?: KitOptions)
```

**Options:**

- `kitPath?: string` - Path to kit executable (default: 'kit')
- `pythonPath?: string` - Path to Python executable (default: 'python3')
- `cwd?: string` - Working directory (default: process.cwd())
- `env?: Record<string, string>` - Environment variables

#### Methods

- `repository(path: string, ref?: string): Repository` - Create a repository instance
- `symbols(path: string, options?: SymbolOptions): Promise<Symbol[]>` - Extract symbols
- `fileTree(path?: string, ref?: string): Promise<FileNode[]>` - Get file tree
- `search(query: string, path?: string, options?: SearchOptions): Promise<SearchResult[]>` - Search for text
- `searchSemantic(path: string, query: string, options?: SemanticSearchOptions): Promise<SemanticSearchResult[]>` - Semantic search
- `usages(symbolName: string, path?: string, options?: UsagesOptions): Promise<any>` - Find symbol usages
- `dependencies(filePath: string, options?: DependenciesOptions): Promise<any>` - Get dependencies
- `export(path?: string, options?: ExportOptions): Promise<any>` - Export repository data
- `reviewPR(prUrl: string, options?: PRReviewOptions): Promise<string>` - Review a PR
- `gitInfo(path?: string, ref?: string): Promise<GitInfo>` - Get git information

### `Repository` Class

Repository-specific operations.

#### Constructor

Created via `kit.repository(path, ref?)`.

#### Methods

All methods from `Kit` class but scoped to the repository path and optional ref.

## Types

### Core Types

```typescript
interface Symbol {
  name: string;
  type: string;
  line: number;
  end_line?: number;
  file?: string;
}

interface FileNode {
  path: string;
  is_dir: boolean;
  size?: number;
}

interface SearchResult {
  file: string;
  line: number;
  column: number;
  match: string;
  context?: string;
}

interface SemanticSearchResult {
  file: string;
  score: number;
  content: string;
  type?: string;
  name?: string;
  line?: number;
}
```

### Option Types

See `types.ts` for complete option interfaces including:

- `SymbolOptions`
- `SearchOptions`
- `SemanticSearchOptions`
- `PRReviewOptions`
- `DependenciesOptions`
- `ExportOptions`

## Examples

### Analyze a Repository

```typescript
import { Kit } from "@runcased/kit";

async function analyzeRepo(repoPath: string) {
  const kit = new Kit();
  const repo = kit.repository(repoPath);

  // Get overview
  const files = await repo.fileTree();
  console.log(`Total files: ${files.filter((f) => !f.is_dir).length}`);

  // Find all classes
  const pythonFiles = files.filter((f) => f.path.endsWith(".py"));

  for (const file of pythonFiles) {
    const symbols = await repo.symbols(file.path, { type: "class" });
    console.log(`${file.path}: ${symbols.length} classes`);
  }
}
```

### Build a Dependency Graph

```typescript
async function buildDependencyGraph(repoPath: string) {
  const kit = new Kit();
  const repo = kit.repository(repoPath);

  const entryPoint = "src/main.ts";
  const deps = await repo.dependencies(entryPoint, {
    direction: "imports",
    transitive: true,
    format: "json",
  });

  console.log(JSON.stringify(deps, null, 2));
}
```

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Run tests
npm test

# Lint
npm run lint
```

## License

MIT - see LICENSE file for details.
