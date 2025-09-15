import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Terminal, CheckCircle, Copy, ArrowRight } from "lucide-react";
import { InstallCursorButton } from "@/components/install-cursor-button";

export default function QuickstartPage() {
  return (
    <div className="prose prose-slate max-w-none">
      <div className="not-prose mb-8">
        <Badge variant="secondary" className="neo-badge bg-yellow-300 text-black mb-4">
          Getting Started
        </Badge>
        <h1 className="text-4xl font-bold mb-4">Quick Start Guide</h1>
        <p className="text-xl text-muted-foreground">
          Get kit-dev-mcp running in under 2 minutes
        </p>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Prerequisites</h2>
        <ul className="space-y-2 text-muted-foreground">
          <li className="flex items-start">
            <CheckCircle className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
            <span>Python 3.8+ installed</span>
          </li>
          <li className="flex items-start">
            <CheckCircle className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
            <span>MCP-compatible AI assistant (Cursor, Windsurf, Claude Code, VS Code)</span>
          </li>
          <li className="flex items-start">
            <CheckCircle className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
            <span>GitHub token (optional, for private repos)</span>
          </li>
        </ul>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Step 1: Install Kit</h2>
        <Tabs defaultValue="pip" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="pip">pip</TabsTrigger>
            <TabsTrigger value="uv">uv (recommended)</TabsTrigger>
            <TabsTrigger value="pipx">pipx</TabsTrigger>
          </TabsList>
          
          <TabsContent value="pip">
            <Card className="neo-card">
              <CardContent className="p-4">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white">
                    <code>pip install "cased-kit{'>'}=2.0.0"</code>
                  </pre>
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  Installs Kit with all features including MCP server support.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="uv">
            <Card className="neo-card">
              <CardContent className="p-4">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white">
                    <code>uv tool install "cased-kit{'>'}=2.0.0"</code>
                  </pre>
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  Installs Kit globally without affecting your system Python. Recommended!
                </p>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="pipx">
            <Card className="neo-card">
              <CardContent className="p-4">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white">
                    <code>pipx install "cased-kit{'>'}=2.0.0"</code>
                  </pre>
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  Alternative to uv for isolated global installation.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Step 2: Configure Your AI Assistant</h2>
        <Tabs defaultValue="cursor" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="cursor">Cursor</TabsTrigger>
            <TabsTrigger value="windsurf">Windsurf</TabsTrigger>
            <TabsTrigger value="claude-code">Claude Code</TabsTrigger>
            <TabsTrigger value="vscode">VS Code</TabsTrigger>
          </TabsList>
          
          <TabsContent value="claude-code">
            <Card className="neo-card">
              <CardHeader>
                <CardTitle className="text-lg">Claude Code Configuration</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Add to your Claude Code MCP configuration:
                </p>
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white text-sm overflow-x-auto">
                    <code>{`{
  "mcpServers": {
    "kit-dev": {
      "command": "uvx",
      "args": ["--from", "cased-kit", "kit-dev-mcp"],
      "env": {
        "OPENAI_API_KEY": "sk-...",              // For get_code_summary (or use ANTHROPIC_API_KEY)
        "KIT_GITHUB_TOKEN": "ghp_..."            // Optional: for private repos
      }
    }
  }
}`}</code>
                  </pre>
                </div>
                <p className="text-sm text-muted-foreground mt-4">
                  Location: <code className="bg-slate-800/50 px-2 py-0.5 rounded text-sm">~/.claude/mcp.json</code>
                </p>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="cursor">
            <Card className="neo-card">
              <CardHeader>
                <CardTitle className="text-lg">Cursor IDE Configuration</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm text-muted-foreground">
                    Add to your Cursor settings:
                  </p>
                  <InstallCursorButton />
                </div>
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white text-sm overflow-x-auto">
                    <code>{`{
  "mcp": {
    "servers": {
      "kit-dev": {
        "command": "uvx",
        "args": ["--from", "cased-kit", "kit-dev-mcp"],
        "env": {
          "OPENAI_API_KEY": "sk-...",              // For get_code_summary (or use ANTHROPIC_API_KEY)
          "KIT_GITHUB_TOKEN": "ghp_..."            // Optional: for private repos
        }
      }
    }
  }
}`}</code>
                  </pre>
                </div>
                <p className="text-sm text-muted-foreground mt-4">
                  <strong>Option 1:</strong> Click "Install into Cursor" above for automatic setup<br/>
                  <strong>Option 2:</strong> Manually add the configuration above to your Cursor settings
                </p>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="windsurf">
            <Card className="neo-card">
              <CardHeader>
                <CardTitle className="text-lg">Windsurf Configuration</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Add to your Windsurf MCP settings:
                </p>
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white text-sm overflow-x-auto">
                    <code>{`{
  "mcp": {
    "servers": {
      "kit-dev": {
        "command": "uvx",
        "args": ["--from", "cased-kit[all]", "kit-dev-mcp"],
        "env": {
          "OPENAI_API_KEY": "sk-...",              // For get_code_summary (or use ANTHROPIC_API_KEY)
          "KIT_GITHUB_TOKEN": "ghp_..."            // Optional: for private repos
        }
      }
    }
  }
}`}</code>
                  </pre>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="vscode">
            <Card className="neo-card">
              <CardHeader>
                <CardTitle className="text-lg">VS Code Configuration</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Add to your VS Code settings (with MCP extension):
                </p>
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white text-sm overflow-x-auto">
                    <code>{`{
  "mcp.servers": {
    "kit-dev": {
      "command": "python",
      "args": ["-m", "kit.mcp.dev"],
      "env": {
        "KIT_GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}`}</code>
                  </pre>
                </div>
                <p className="text-sm text-muted-foreground mt-4">
                  Requires the MCP extension for VS Code.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Step 3: Test Your Setup</h2>
        <Card className="neo-card">
          <CardContent className="p-6">
            <p className="text-muted-foreground mb-4">
              Start a conversation with your AI and test these commands:
            </p>
            <div className="space-y-3">
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                <code className="text-white">Using Kit, open my project</code>
              </div>
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                <code className="text-white">Using Kit, show me the file structure</code>
              </div>
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                <code className="text-white">Using Kit, extract symbols from the main file</code>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-4">
              If these work, you're all set! Your AI now has access to Kit's powerful code intelligence tools.
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">What's Next?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link href="/docs/system-prompts" className="block">
            <Card className="neo-card hover:shadow-lg transition-shadow cursor-pointer group">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-2 group-hover:text-red-500 transition-colors">
                  Optimize with System Prompts
                </h3>
                <p className="text-sm text-muted-foreground mb-3">
                  Configure your AI to automatically use Kit tools
                </p>
                <div className="text-sm font-mono-accent text-red-600">
                  <span className="font-mono">docs/system-prompts</span>
                </div>
              </CardContent>
            </Card>
          </Link>
          
          <Link href="/docs/tools" className="block">
            <Card className="neo-card hover:shadow-lg transition-shadow cursor-pointer group">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-2 group-hover:text-red-500 transition-colors">
                  Explore Available Tools
                </h3>
                <p className="text-sm text-muted-foreground mb-3">
                  Learn about all the tools at your disposal
                </p>
                <div className="text-sm font-mono-accent text-red-600">
                  <span className="font-mono">tools</span>
                </div>
              </CardContent>
            </Card>
          </Link>
          
          <Link href="/docs/repository" className="block">
            <Card className="neo-card hover:shadow-lg transition-shadow cursor-pointer group">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-2 group-hover:text-red-500 transition-colors">
                  Repository Management
                </h3>
                <p className="text-sm text-muted-foreground mb-3">
                  Work with local and remote repositories
                </p>
                <div className="text-sm font-mono-accent text-red-600">
                  <span className="font-mono">docs/repository</span>
                </div>
              </CardContent>
            </Card>
          </Link>
          
          <Link href="/docs/research" className="block">
            <Card className="neo-card hover:shadow-lg transition-shadow cursor-pointer group">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-2 group-hover:text-red-500 transition-colors">
                  Documentation Research
                </h3>
                <p className="text-sm text-muted-foreground mb-3">
                  Multi-source documentation aggregation
                </p>
                <div className="text-sm font-mono-accent text-red-600">
                  <span className="font-mono">docs/research</span>
                </div>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>

      <Card className="neo-card my-8 bg-gradient-to-r from-red-600 to-blue-600 text-white border-0">
        <CardContent className="p-8 text-center">
          <Terminal className="h-12 w-12 mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-4">
            You're Ready to Build!
          </h2>
          <p className="mb-6">
            Your AI assistant now has access to Kit's powerful code intelligence.
            Start building with better context!
          </p>
        </CardContent>
      </Card>
    </div>
  );
}