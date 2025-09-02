import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Settings, Key, Database, Globe, Folder } from "lucide-react";

export default function ConfigurationPage() {
  return (
    <div className="prose prose-slate max-w-none">
      <div className="not-prose mb-8">
        <Badge variant="secondary" className="neo-badge bg-yellow-300 text-black mb-4">
          Configuration
        </Badge>
        <h1 className="text-4xl font-bold mb-4">Configuration Guide</h1>
        <p className="text-xl text-muted-foreground">
          Configure kit-mcp-dev for your development environment
        </p>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Environment Variables</h2>
        <div className="not-prose space-y-4">
          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5 text-primary" />
                LLM API Keys (Required for get_code_summary)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">
                An LLM API key is required for the <code className="text-xs bg-gray-100 px-1 rounded">get_code_summary</code> tool. Choose one of:
              </p>
              <div className="space-y-2">
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <code className="text-white"># Option 1: OpenAI (default)
export OPENAI_API_KEY="sk-..."</code>
                </div>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <code className="text-white"># Option 2: Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."</code>
                </div>
                <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                  <code className="text-white"># Option 3: Google Gemini
export GOOGLE_API_KEY="AI..."</code>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Note: All other tools work without an LLM API key.
              </p>
            </CardContent>
          </Card>

          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5 text-primary" />
                KIT_GITHUB_TOKEN
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">
                GitHub personal access token for accessing private repositories and increasing API rate limits.
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                <code className="text-white">export KIT_GITHUB_TOKEN="ghp_your_token_here"</code>
              </div>
            </CardContent>
          </Card>

          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5 text-primary" />
                KIT_CACHE_DIR
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">
                Directory for caching symbol extraction and documentation. Defaults to ~/.cache/kit
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                <code className="text-white">export KIT_CACHE_DIR="~/.cache/kit"</code>
              </div>
            </CardContent>
          </Card>

          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5 text-primary" />
                KIT_USE_CONTEXT7
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">
                Enable context7.com integration for AI-aggregated documentation. Defaults to true.
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-3 font-mono text-sm">
                <code className="text-white">export KIT_USE_CONTEXT7="true"</code>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">MCP Server Configuration</h2>
        <Tabs defaultValue="cursor" className="w-full not-prose">
          <TabsList className="grid grid-cols-3 w-full">
            <TabsTrigger value="cursor">Cursor</TabsTrigger>
            <TabsTrigger value="claude-code">Claude Code</TabsTrigger>
            <TabsTrigger value="vscode">VS Code</TabsTrigger>
          </TabsList>

          <TabsContent value="cursor">
            <Card className="neo-card">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-3">Cursor Configuration</h3>
                <p className="text-sm text-muted-foreground mb-3">Add to your Cursor settings.json</p>
                <div className="border-2 border-black bg-black p-4 font-mono text-sm">
                  <pre className="text-white overflow-x-auto">
{`{
  "mcpServers": {
    "kit-dev": {
      "command": "uvx",
      "args": ["--from", "cased-kit[all]", "kit-mcp-dev"],
      "env": {
        "OPENAI_API_KEY": "sk-...",              // For get_code_summary (or use ANTHROPIC_API_KEY)
        "KIT_GITHUB_TOKEN": "ghp_..."            // Optional: for private repos
      }
    }
  }
}`}</pre>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="claude-code">
            <Card className="neo-card">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-3">Claude Code Configuration</h3>
                <p className="text-sm text-muted-foreground mb-3">Add to your Claude Desktop config</p>
                <div className="border-2 border-black bg-black p-4 font-mono text-sm">
                  <pre className="text-white overflow-x-auto">
{`{
  "mcpServers": {
    "kit-dev": {
      "command": "uvx",
      "args": ["--from", "cased-kit[all]", "kit-mcp-dev"],
      "env": {
        "OPENAI_API_KEY": "sk-...",              // For get_code_summary (or use ANTHROPIC_API_KEY)
        "KIT_GITHUB_TOKEN": "ghp_..."            // Optional: for private repos
      }
    }
  }
}`}</pre>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="vscode">
            <Card className="neo-card">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-3">VS Code Configuration</h3>
                <p className="text-sm text-muted-foreground mb-3">Add to VS Code settings.json (requires MCP extension)</p>
                <div className="border-2 border-black bg-black p-4 font-mono text-sm">
                  <pre className="text-white overflow-x-auto">
{`{
  "mcp.servers": {
    "kit-dev": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "cased-kit[all]", "kit-mcp-dev"],
      "env": {
        "OPENAI_API_KEY": "sk-...",              // For get_code_summary (or use ANTHROPIC_API_KEY)
        "KIT_GITHUB_TOKEN": "ghp_..."            // Optional: for private repos
      }
    }
  }
}`}</pre>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

        </Tabs>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Advanced Configuration Options</h2>
        <Card className="neo-card not-prose">
          <CardContent className="p-6">
            <h3 className="font-semibold mb-3">Environment Variables for Advanced Users</h3>
            <div className="border-2 border-black bg-black p-4 font-mono text-sm mb-4">
              <pre className="text-white overflow-x-auto">
{`{
  "env": {
    "KIT_GITHUB_TOKEN": "ghp_...",           // GitHub access token
    "KIT_CACHE_DIR": "~/.cache/kit",         // Cache directory  
    "KIT_USE_CONTEXT7": "true",              // Enable context7.com
    "KIT_LOG_LEVEL": "DEBUG",                // Logging level
    "KIT_MAX_WORKERS": "8",                  // Parallel workers
    "KIT_CACHE_TTL": "3600",                 // Cache TTL in seconds
    "KIT_DEEP_RESEARCH": "true"              // Deep doc research
  }
}`}</pre>
            </div>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p><strong>KIT_LOG_LEVEL:</strong> Set to DEBUG for verbose logging</p>
              <p><strong>KIT_MAX_WORKERS:</strong> Number of parallel workers (default: 4)</p>
              <p><strong>KIT_CACHE_TTL:</strong> Cache time-to-live in seconds</p>
              <p><strong>KIT_DEEP_RESEARCH:</strong> Enable deep documentation research</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">File Watching Configuration</h2>
        <Card className="not-prose">
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground mb-4">
              Configure which files to watch and ignore:
            </p>
            <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
              <pre className="text-white">
{`# .kitignore file in your project root
node_modules/
.git/
*.pyc
__pycache__/
.venv/
dist/
build/
*.log
.DS_Store`}</pre>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Performance Tuning</h2>
        <div className="not-prose grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="neo-card">
            <CardHeader>
              <CardTitle>Cache Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Enable aggressive caching for large repos</li>
                <li>• Set appropriate TTL values</li>
                <li>• Use local SSD for cache directory</li>
                <li>• Clear cache periodically</li>
              </ul>
            </CardContent>
          </Card>

          <Card className="neo-card">
            <CardHeader>
              <CardTitle>Memory Management</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Adjust worker count based on CPU cores</li>
                <li>• Limit file size for analysis</li>
                <li>• Configure max memory usage</li>
                <li>• Enable incremental processing</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}