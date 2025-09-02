import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Terminal, Sparkles, CheckCircle } from "lucide-react";
import Link from "next/link";

export default function DocsPage() {
  return (
    <div className="prose prose-slate max-w-none px-4 sm:px-0">
      <div className="not-prose mb-8">
        <Badge variant="secondary" className="mb-4 neo-badge bg-yellow-300 text-black">
          Version 2.0
        </Badge>
        <h1 className="text-2xl sm:text-4xl font-bold mb-4 break-words">kit-mcp-dev Documentation</h1>
        <p className="text-sm sm:text-xl text-muted-foreground break-words">
          The most comprehensive MCP server with Kit's production-grade code intelligence
        </p>
      </div>

      <div className="my-8">
        <h2 className="text-xl sm:text-2xl font-bold mb-4">What is kit-mcp-dev?</h2>
        <p className="text-sm sm:text-base text-muted-foreground mb-6 break-words">
          kit-mcp-dev provides your AI assistant with <strong>comprehensive development tools</strong>: repository indexing, 
          file trees, fast cached symbol extraction, dependency analysis, semantic search, and deep documentation 
          research using powerful LLMs. All running locally, privately, and for free (just pay for tokens).
        </p>
      </div>

      <Card className="my-8 neo-card">
        <CardContent className="p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold mb-4">Comprehensive Development Tools</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-start space-x-2">
              <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
              <div>
                <strong>Repository Management</strong>
                <p className="text-sm text-muted-foreground">Open local & remote repositories</p>
              </div>
            </div>
            <div className="flex items-start space-x-2">
              <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
              <div>
                <strong>File Trees & Navigation</strong>
                <p className="text-sm text-muted-foreground">Kit's structured file exploration</p>
              </div>
            </div>
            <div className="flex items-start space-x-2">
              <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
              <div>
                <strong>Fast Symbol Extraction</strong>
                <p className="text-sm text-muted-foreground">Smart incremental caching for instant results</p>
              </div>
            </div>
            <div className="flex items-start space-x-2">
              <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
              <div>
                <strong>Deep Documentation Research</strong>
                <p className="text-sm text-muted-foreground">Official docs + GitHub + tutorials + SO</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="my-8">
        <h2 className="text-xl sm:text-2xl font-bold mb-4">Installation</h2>
        <Tabs defaultValue="pip" className="w-full">
          <TabsList className="grid grid-cols-3 w-full">
            <TabsTrigger value="pip">pip</TabsTrigger>
            <TabsTrigger value="uv">uv</TabsTrigger>
            <TabsTrigger value="source">From Source</TabsTrigger>
          </TabsList>
          <TabsContent value="pip">
            <Card className="neo-card">
              <CardContent className="p-4">
                <pre className="border-2 border-black bg-black text-white p-2 sm:p-4 overflow-x-auto text-xs sm:text-sm">
                  <code>{`# Install kit with MCP server
pip install cased-kit`}</code>
                </pre>
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="uv">
            <Card className="neo-card">
              <CardContent className="p-4">
                <pre className="border-2 border-black bg-black text-white p-2 sm:p-4 overflow-x-auto text-xs sm:text-sm">
                  <code>{`# Install globally with uv
uv tool install cased-kit

# The kit-mcp-dev command will be available globally`}</code>
                </pre>
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="source">
            <Card className="neo-card">
              <CardContent className="p-4">
                <pre className="border-2 border-black bg-black text-white p-2 sm:p-4 overflow-x-auto text-xs sm:text-sm">
                  <code>{`git clone https://github.com/cased/kit.git
cd kit
uv venv .venv
source .venv/bin/activate
uv pip install -e .
# Then run: kit-mcp-dev`}</code>
                </pre>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Configuration</h2>
        <p className="text-muted-foreground mb-4">
          Add kit-mcp-dev to your AI assistant's configuration:
        </p>
        <Tabs defaultValue="cursor" className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="cursor">Cursor</TabsTrigger>
            <TabsTrigger value="claude">Claude Code</TabsTrigger>
            <TabsTrigger value="vscode">VS Code</TabsTrigger>
          </TabsList>
          <TabsContent value="cursor">
            <Card>
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground mb-2">Location: ~/.cursor/mcp.json</p>
                <pre className="border-2 border-black bg-black text-white text-sm p-4 rounded-lg overflow-x-auto">
                  <code>{`{
  "mcpServers": {
    "kit-dev": {
      "command": "uvx",
      "args": ["--from", "cased-kit", "kit-mcp-dev"],
      "env": {
        "OPENAI_API_KEY": "sk-...",              // For get_code_summary (or use ANTHROPIC_API_KEY)
        "KIT_GITHUB_TOKEN": "ghp_..."            // Optional: for private repos
      }
    }
  }
}`}</code>
                </pre>
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="claude">
            <Card>
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground mb-2">
                  Mac: ~/Library/Application Support/Claude/claude_desktop_config.json
                </p>
                <pre className="border-2 border-black bg-black text-white text-sm p-4 rounded-lg overflow-x-auto">
                  <code>{`{
  "mcpServers": {
    "kit-dev": {
      "command": "uvx",
      "args": ["--from", "cased-kit", "kit-mcp-dev"],
      "env": {
        "OPENAI_API_KEY": "sk-...",              // For get_code_summary (or use ANTHROPIC_API_KEY)
        "KIT_GITHUB_TOKEN": "ghp_..."            // Optional: for private repos
      }
    }
  }
}`}</code>
                </pre>
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="vscode">
            <Card>
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground mb-2">Location: .vscode/mcp.json (workspace)</p>
                <pre className="border-2 border-black bg-black text-white text-sm p-4 rounded-lg overflow-x-auto">
                  <code>{`{
  "mcp": {
    "servers": {
      "kit-dev": {
        "type": "stdio",
        "command": "uvx",
        "args": ["--from", "cased-kit", "kit-mcp-dev"],
        "env": {
          "OPENAI_API_KEY": "sk-...",              // For get_code_summary (or use ANTHROPIC_API_KEY)
          "KIT_GITHUB_TOKEN": "ghp_..."            // Optional: for private repos
        }
      }
    }
  }
}`}</code>
                </pre>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">How It Works</h2>
        <p className="text-muted-foreground mb-4">
          kit-mcp-dev provides a comprehensive set of tools that your AI assistant can use to 
          understand and work with your codebase:
        </p>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>When you start a conversation, the MCP server initializes with your repository</li>
          <li>Your AI can use tools to watch files, search code, build context, and more</li>
          <li>Results are returned in real-time, giving your AI deep context about your code</li>
          <li>The AI uses this information to provide better suggestions and implementations</li>
        </ol>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Next Steps</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link href="/docs/quickstart" className="block">
            <Card className="neo-card h-full">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-2">Quick Start Guide</h3>
                <p className="text-sm text-muted-foreground">
                  Get up and running in under 2 minutes
                </p>
              </CardContent>
            </Card>
          </Link>
          <Link href="/tools" className="block">
            <Card className="neo-card h-full">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-2">Available Tools</h3>
                <p className="text-sm text-muted-foreground">
                  Explore all the tools at your AI's disposal
                </p>
              </CardContent>
            </Card>
          </Link>
          <Link href="/docs/examples" className="block">
            <Card className="neo-card h-full">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-2">Examples</h3>
                <p className="text-sm text-muted-foreground">
                  See real-world usage examples
                </p>
              </CardContent>
            </Card>
          </Link>
          <Link href="/docs/api" className="block">
            <Card className="neo-card h-full">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-2">API Reference</h3>
                <p className="text-sm text-muted-foreground">
                  Deep dive into the technical details
                </p>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>
    </div>
  );
}