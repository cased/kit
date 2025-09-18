import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, Code, FileText, FileSearch, Key, Sparkles } from "lucide-react";

export default function PackageSearchPage() {
  return (
    <div className="prose prose-slate max-w-none">
      <div className="not-prose mb-8">
        <Badge variant="secondary" className="neo-badge bg-blue-300 text-black mb-4">
          New Feature
        </Badge>
        <h1 className="text-4xl font-bold mb-4">Chroma Package Search</h1>
        <p className="text-xl text-muted-foreground">
          Search and explore source code from popular packages directly through MCP
        </p>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Overview</h2>
        <p className="text-muted-foreground mb-6">
          kit-dev-mcp now integrates with Chroma's Package Search API to provide powerful source code
          exploration capabilities. Search through the actual source code of popular packages using
          regex patterns, semantic search, or read specific files directly.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="neo-card border-2 border-blue-500">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Search className="h-5 w-5 text-blue-500" />
                package_search_grep
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Use regex patterns to find specific code patterns across package source files.
              </p>
            </CardContent>
          </Card>

          <Card className="neo-card border-2 border-purple-500">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Sparkles className="h-5 w-5 text-purple-500" />
                package_search_hybrid
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Semantic search with optional regex filtering for intelligent code exploration.
              </p>
            </CardContent>
          </Card>

          <Card className="neo-card border-2 border-green-500">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="h-5 w-5 text-green-500" />
                package_search_read_file
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Read specific files or line ranges from package source code.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Configuration</h2>

        <Card className="neo-card border-2 border-amber-500">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5 text-amber-500" />
              API Key Setup
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              To use Package Search features, you need a Chroma API key. Get one from the{" "}
              <a href="https://cloud.trychroma.com" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                Chroma Cloud dashboard
              </a>.
            </p>

            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">For Cursor/Windsurf/Claude Code</h4>
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white">
{`{
  "mcpServers": {
    "kit-dev-mcp": {
      "command": "uvx",
      "args": ["--from", "cased-kit", "kit-dev-mcp"],
      "env": {
        "CHROMA_PACKAGE_SEARCH_API_KEY": "your_api_key_here"
      }
    }
  }
}`}</pre>
                </div>
              </div>

              <div>
                <h4 className="font-semibold mb-2">For Command Line</h4>
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white">
{`export CHROMA_PACKAGE_SEARCH_API_KEY="your_api_key_here"
# or
export CHROMA_API_KEY="your_api_key_here"  # Fallback`}</pre>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Usage Examples</h2>

        <div className="space-y-6">
          {/* Grep Search Example */}
          <div>
            <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
              <Search className="h-4 w-4 text-blue-500" />
              Grep Search - Find Code Patterns
            </h3>
            <Card className="not-prose">
              <CardContent className="p-4">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white">
{`# Find all async functions in FastAPI
package_search_grep({
  "package": "fastapi",
  "pattern": "async def \\\\w+",
  "max_results": 20,
  "file_pattern": "*.py"
})

# Find class definitions extending BaseModel
package_search_grep({
  "package": "pydantic",
  "pattern": "class \\\\w+\\\\(BaseModel\\\\)",
  "max_results": 10
})

# Search for specific decorators
package_search_grep({
  "package": "django",
  "pattern": "@login_required",
  "case_sensitive": true
})`}</pre>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Hybrid Search Example */}
          <div>
            <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-purple-500" />
              Hybrid Search - Semantic + Pattern
            </h3>
            <Card className="not-prose">
              <CardContent className="p-4">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white">
{`# Find authentication-related code
package_search_hybrid({
  "package": "django",
  "query": "user authentication and session management",
  "max_results": 15
})

# Search with regex filter
package_search_hybrid({
  "package": "numpy",
  "query": "fast fourier transform implementation",
  "regex_filter": "def .*fft",
  "max_results": 10
})

# Explore specific functionality
package_search_hybrid({
  "package": "tensorflow",
  "query": "gradient computation and backpropagation",
  "file_pattern": "*.py"
})`}</pre>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Read File Example */}
          <div>
            <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
              <FileSearch className="h-4 w-4 text-green-500" />
              Read Files - Get Full Context
            </h3>
            <Card className="not-prose">
              <CardContent className="p-4">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white">
{`# Read entire file
package_search_read_file({
  "package": "requests",
  "file_path": "requests/models.py"
})

# Read specific line range
package_search_read_file({
  "package": "flask",
  "file_path": "flask/app.py",
  "start_line": 100,
  "end_line": 200
})

# Read package initialization
package_search_read_file({
  "package": "pandas",
  "file_path": "pandas/__init__.py",
  "start_line": 1,
  "end_line": 50
})`}</pre>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Integration with deep_research_package</h2>
        <Card className="neo-card border-2 border-indigo-500">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code className="h-5 w-5 text-indigo-500" />
              Automatic Multi-Source Research
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              When you have a Chroma API key configured, `deep_research_package` automatically
              combines results from both Chroma Package Search and Context7 documentation:
            </p>
            <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
              <pre className="text-white">
{`# Automatically uses both sources when available
deep_research_package({
  "package_name": "numpy",
  "query": "How does FFT work?"
})

# Returns combined results:
{
  "package": "numpy",
  "source": "multi_source+llm",
  "providers": ["ChromaPackageSearch", "UpstashProvider"],
  "chroma_results": [...],  // Source code snippets
  "documentation": {...},    // Context7 docs
  "answer": "..."           // LLM synthesis
}`}</pre>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Available Packages</h2>
        <p className="text-muted-foreground mb-4">
          Chroma Package Search includes popular packages across multiple languages:
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { lang: "Python", packages: ["numpy", "django", "fastapi", "requests", "pandas", "tensorflow", "pytorch"] },
            { lang: "JavaScript", packages: ["react", "vue", "express", "next.js", "node"] },
            { lang: "TypeScript", packages: ["@types/*", "typescript"] },
            { lang: "More", packages: ["And many others..."] }
          ].map(({ lang, packages }) => (
            <Card key={lang} className="neo-card">
              <CardHeader className="py-3">
                <CardTitle className="text-sm">{lang}</CardTitle>
              </CardHeader>
              <CardContent className="py-3">
                <ul className="text-xs text-muted-foreground space-y-1">
                  {packages.map(pkg => (
                    <li key={pkg}>• {pkg}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      <div className="my-8 p-6 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border-2 border-blue-200">
        <h3 className="text-lg font-bold mb-2">
          💡 Pro Tips
        </h3>
        <ul className="text-sm text-muted-foreground space-y-2">
          <li>• Use <code>package_search_hybrid</code> for exploring unfamiliar codebases</li>
          <li>• Use <code>package_search_grep</code> when you know exact patterns</li>
          <li>• Combine with <code>deep_research_package</code> for comprehensive understanding</li>
          <li>• Results are cached for better performance on repeated searches</li>
        </ul>
      </div>
    </div>
  );
}