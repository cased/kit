import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Code2, FileJson, Package } from "lucide-react";

export default function ApiPage() {
  return (
    <div className="prose prose-slate max-w-none">
      <div className="not-prose mb-8">
        <Badge variant="secondary" className="neo-badge bg-yellow-300 text-black mb-4">
          API Reference
        </Badge>
        <h1 className="text-4xl font-bold mb-4">API Reference</h1>
        <p className="text-xl text-muted-foreground">
          Complete reference for kit-dev-mcp tools and responses
        </p>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Repository Operations</h2>
        
        <Card className="neo-card not-prose mb-6">
          <CardHeader>
            <CardTitle className="font-mono">open_repository</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">Parameters</h4>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <pre className="text-white">
{`{
  "path": string,           // Required: local path or GitHub URL
  "github_token": string,   // Optional: for private repos
  "ref": string            // Optional: branch/tag/commit
}`}</pre>
                </div>
              </div>
              
              <div>
                <h4 className="font-semibold mb-2">Returns</h4>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <pre className="text-white">
{`{
  "repo_id": string,
  "path": string,
  "type": "local" | "github",
  "file_count": number,
  "language_stats": {
    "Python": 45.2,
    "JavaScript": 30.1,
    ...
  }
}`}</pre>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="neo-card not-prose mb-6">
          <CardHeader>
            <CardTitle className="font-mono">get_file_tree</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">Parameters</h4>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <pre className="text-white">
{`{
  "repo_id": string,        // Required: repository identifier
  "path": string,          // Optional: subdirectory path
  "max_depth": number      // Optional: tree depth limit
}`}</pre>
                </div>
              </div>
              
              <div>
                <h4 className="font-semibold mb-2">Returns</h4>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <pre className="text-white">
{`[
  {
    "path": "src/main.py",
    "type": "file",
    "size": 2048,
    "last_modified": "2024-01-15T10:30:00Z"
  },
  {
    "path": "src/utils",
    "type": "directory",
    "children": [...]
  }
]`}</pre>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Documentation Research</h2>
        
        <Card className="neo-card not-prose mb-6">
          <CardHeader>
            <CardTitle className="font-mono">deep_research_package</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">Parameters</h4>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <pre className="text-white">
{`{
  "package_name": string,    // Required: package to research
  "max_sources": number      // Optional: max sources to fetch
}`}</pre>
                </div>
              </div>
              
              <div>
                <h4 className="font-semibold mb-2">Returns</h4>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <pre className="text-white">
{`{
  "package": "react",
  "sources_found": 8,
  "quality_score": 0.92,
  "documentation": {
    "overview": "React is a JavaScript library...",
    "installation": "npm install react",
    "api_reference": {...},
    "examples": [...],
    "best_practices": [...]
  },
  "sources": [
    {
      "type": "official",
      "url": "https://react.dev",
      "reliability": 1.0
    }
  ],
  "output_file": "/path/to/cache/react_docs.json"
}`}</pre>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Code Intelligence</h2>
        
        <Card className="neo-card not-prose mb-6">
          <CardHeader>
            <CardTitle className="font-mono">extract_symbols</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">Parameters</h4>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <pre className="text-white">
{`{
  "repo_id": string,         // Required
  "file_path": string,       // Required
  "symbol_type": string      // Optional: "function" | "class" | "all"
}`}</pre>
                </div>
              </div>
              
              <div>
                <h4 className="font-semibold mb-2">Returns</h4>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <pre className="text-white">
{`{
  "symbols": [
    {
      "name": "authenticate",
      "type": "function",
      "line": 15,
      "docstring": "Authenticate user credentials",
      "parameters": ["username", "password"],
      "returns": "User | None"
    },
    {
      "name": "User",
      "type": "class",
      "line": 5,
      "docstring": "User model class",
      "methods": ["__init__", "validate", "save"],
      "attributes": ["id", "username", "email"]
    }
  ],
  "imports": [
    "from datetime import datetime",
    "import jwt"
  ],
  "metrics": {
    "complexity": 5,
    "lines_of_code": 150
  }
}`}</pre>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Search Operations</h2>
        
        <Card className="neo-card not-prose mb-6">
          <CardHeader>
            <CardTitle className="font-mono">grep_ast</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">Parameters</h4>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <pre className="text-white">
{`{
  "repo_id": string,        // Required: repository identifier
  "pattern": string,        // Required: AST pattern to search
  "file_pattern": string,   // Optional: glob pattern for files
  "language": string        // Optional: programming language
}`}</pre>
                </div>
              </div>
              
              <div>
                <h4 className="font-semibold mb-2">Returns</h4>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <pre className="text-white">
{`{
  "matches": [
    {
      "file": "src/main.py",
      "line": 42,
      "text": "async def handle_request(req):",
      "match_type": "async_function_def"
    }
  ],
  "total_matches": 15,
  "files_searched": 120
}`}</pre>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="neo-card not-prose mb-6">
          <CardHeader>
            <CardTitle className="font-mono">search_code</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">Parameters</h4>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <pre className="text-white">
{`{
  "repo_id": string,        // Required: repository identifier
  "pattern": string,        // Required: regex pattern
  "max_results": number,    // Optional: limit results
  "case_sensitive": boolean // Optional: case sensitivity
}`}</pre>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Error Responses</h2>
        <Card className="neo-card not-prose">
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground mb-4">
              All tools return standardized error responses:
            </p>
            <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
              <pre className="text-white">
{`{
  "error": {
    "code": "REPOSITORY_NOT_FOUND",
    "message": "Repository with ID 'repo_123' not found",
    "details": {
      "repo_id": "repo_123",
      "available_repos": ["repo_456", "repo_789"]
    }
  }
}`}</pre>
            </div>
            
            <div className="mt-4">
              <h4 className="font-semibold mb-2">Common Error Codes</h4>
              <ul className="space-y-1 text-sm text-muted-foreground">
                <li><code className="bg-slate-800 px-1 rounded">REPOSITORY_NOT_FOUND</code> - Repository doesn't exist</li>
                <li><code className="bg-slate-800 px-1 rounded">FILE_NOT_FOUND</code> - File doesn't exist in repository</li>
                <li><code className="bg-slate-800 px-1 rounded">INVALID_PARAMETERS</code> - Missing or invalid parameters</li>
                <li><code className="bg-slate-800 px-1 rounded">PERMISSION_DENIED</code> - No access to resource</li>
                <li><code className="bg-slate-800 px-1 rounded">RATE_LIMITED</code> - API rate limit exceeded</li>
                <li><code className="bg-slate-800 px-1 rounded">TIMEOUT</code> - Operation timed out</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}