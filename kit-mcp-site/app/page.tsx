"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Terminal, 
  Shield, 
  Zap, 
  GitBranch, 
  Eye,
  TestTube,
  Search,
  BookOpen,
  Sparkles,
  ArrowRight,
  CheckCircle,
  Github,
  FileCode2,
  Activity,
  Lock,
  RefreshCw,
  Layers
} from "lucide-react";
import Link from "next/link";
import { useState, useEffect } from "react";

export default function Home() {
  const [activeDemo, setActiveDemo] = useState("symbols");
  const [typedText, setTypedText] = useState("");
  const fullText = "The best MCP server for coding with AI agents";
  
  // Create the Cursor deep link config
  const cursorConfig = {
    "kit-mcp-dev": {
      "command": "uvx",
      "args": ["--from", "cased-kit", "kit-mcp-dev"]
    }
  };
  const encodedConfig = typeof window !== 'undefined' 
    ? btoa(JSON.stringify(cursorConfig))
    : '';
  const cursorDeepLink = `cursor://settings/mcp/install?server=${encodeURIComponent(encodedConfig)}`;
  
  useEffect(() => {
    let index = 0;
    const timer = setInterval(() => {
      if (index <= fullText.length) {
        setTypedText(fullText.slice(0, index));
        index++;
      } else {
        clearInterval(timer);
      }
    }, 50);
    return () => clearInterval(timer);
  }, []);

  const features = [
    {
      icon: <Layers className="h-5 w-5" />,
      title: "Production-Grade Code Intelligence",
      description: "kit's battle-tested repository analysis, symbol extraction, and dependency mapping"
    },
    {
      icon: <BookOpen className="h-5 w-5" />,
      title: "Tiered Deep Research",
      description: "LLM-powered comprehensive documentation research. Get detailed answers about any package using AI. Local LLM support. Just pay for tokens, if anything."
    },
    {
      icon: <FileCode2 className="h-5 w-5" />,
      title: "Smart Context Building",
      description: "Automatically gather relevant code, docs, and examples for any task"
    },
    {
      icon: <RefreshCw className="h-5 w-5" />,
      title: "Always Up-to-Date",
      description: "Real-time repository state, current documentation, and fresh examples"
    },
    {
      icon: <Search className="h-5 w-5" />,
      title: "Semantic Code Search",
      description: "Find code by meaning, not just keywords - powered by AI embeddings"
    },
    {
      icon: <Zap className="h-5 w-5" />,
      title: "Fast Incremental Symbol Extraction",
      description: "Smart caching system for instant code understanding"
    }
  ];

  const tools = [
    { name: "open_repository", description: "Open local and remote repositories" },
    { name: "get_file_tree", description: "Structured file navigation" },
    { name: "extract_symbols", description: "Fast symbol extraction with caching" },
    { name: "search_code", description: "Powerful regex search across codebase" },
    { name: "grep_code", description: "Fast literal search with smart filtering" },
    { name: "get_file_content", description: "Read single or multiple files" },
    { name: "get_multiple_file_contents", description: "Bulk file operations" },
    { name: "find_symbol_usages", description: "Track symbol usage everywhere" },
    { name: "get_code_summary", description: "AI-powered code summaries" },
    { name: "get_git_info", description: "Git repository metadata" },
    { name: "review_diff", description: "AI-powered git diff review" },
    { name: "watch_files", description: "Real-time file change monitoring" },
    { name: "get_file_changes", description: "Recent file change history" },
    { name: "semantic_search", description: "AI-powered search by meaning" },
    { name: "deep_research_package", description: "Comprehensive package documentation using LLM" },
    { name: "build_smart_context", description: "Task-aware context building" }
  ];

  return (
    <div className="min-h-screen bg-white relative dotted-pattern">
      {/* Subtle scan line effect */}
      <div className="scan-line pointer-events-none fixed inset-0 z-0 opacity-30"></div>
      {/* Navigation */}
      <nav className="sticky top-0 z-50 w-full border-b-4 border-black bg-white">
        <div className="container flex h-16 items-center px-4">
          <div className="flex items-center space-x-1 sm:space-x-2">
            <Terminal className="h-5 w-5 sm:h-6 sm:w-6 text-primary flex-shrink-0" />
            <span className="font-bold text-sm sm:text-xl whitespace-nowrap">kit-dev for mcp</span>
          </div>
          <div className="ml-auto flex items-center space-x-1 sm:space-x-3">
            <Button variant="ghost" size="sm" className="px-2 sm:px-4 neo-button" asChild>
              <Link href="/docs">
                <span className="sm:hidden">Docs</span>
                <span className="hidden sm:inline">Documentation</span>
              </Link>
            </Button>
            <Button variant="ghost" size="sm" className="px-2 sm:px-4 neo-button" asChild>
              <Link href="/tools">Tools</Link>
            </Button>
            <Button variant="ghost" size="sm" className="px-2 sm:px-4 neo-button" asChild>
              <Link href="https://github.com/cased/kit" target="_blank">
                <Github className="h-4 w-4 sm:mr-2" />
                <span className="hidden sm:inline">GitHub</span>
              </Link>
            </Button>
            <Button size="sm" className="hidden sm:flex neo-button bg-red-400" asChild>
              <Link href="/docs/quickstart">Get Started</Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container px-4 pt-16 pb-12">
        <div className="mx-auto max-w-5xl text-center">
          <Badge className="mb-3 neo-badge bg-white text-black" variant="secondary">
            <span>
              New
              {" open source from "}
              <Link href="https://cased.com" className="text-blue-500 hover:text-blue-600">Cased</Link>, built on <Link href="https://github.com/cased/kit" className="text-blue-500 hover:text-blue-600">cased-kit</Link>
            </span>
          </Badge>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight bg-gradient-to-r from-red-600 via-blue-500 to-red-600 bg-clip-text text-transparent pb-2 animate-shimmer bg-[length:200%_100%]">
            kit-dev for mcp
          </h1>
          <p className="mt-6 text-xl md:text-2xl text-muted-foreground h-8">
            {typedText}
          </p>
          <p className="mt-6 text-lg text-muted-foreground max-w-3xl mx-auto">
            <span className="mt-4 text-lg text-muted-foreground max-w-3xl mx-auto font-bold">
            100% local, private, and free. MIT licensed from <Link href="https://cased.com" className="text-blue-500 hover:text-blue-600">Cased</Link>.
            </span>
          </p>
          
          {/* Quick Install */}
          <div className="mt-6 mb-6 mx-auto max-w-2xl">
            <div className="border border-gray-600 bg-black p-3 font-mono text-sm rounded-lg">
              <div className="flex items-center justify-between">
                <code className="text-white text-xs sm:text-sm font-bold">
                  uvx --from cased-kit kit-mcp-dev
                </code>
                <Link 
                  href="/docs"
                  className="text-blue-400 hover:text-blue-300 text-xs ml-4 whitespace-nowrap transition-colors"
                >
                  Setup Guide →
                </Link>
              </div>
            </div>
          </div>
          
          <div className="mt-6 flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="neo-button bg-blue-400 text-black" asChild>  
              <Link href="/docs/quickstart">
                Quick Start Guide
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" className="neo-button bg-white" variant="outline" asChild>
              <Link href="/docs">
                Documentation
                <FileCode2 className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="container px-4 py-12 neo-section">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold">Context Is Everything</h2>
            <p className="mt-3 text-lg text-muted-foreground">
            kit's production-grade code intelligence, multi-source documentation research, and 
            context building. <br />Now in an overpowered local MCP server, for free,
            for use with any coding agent.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <Card key={i} className="border-2 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                <CardHeader>
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-primary/10 rounded-lg text-primary">
                      {feature.icon}
                    </div>
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription>{feature.description}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Interactive Demo */}
      <section id="demo" className="container px-4 py-12 neo-section">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold">Context Building in Action</h2>
            <p className="mt-3 text-lg text-muted-foreground">
              See how kit-dev gathers the right context for any development task
            </p>
          </div>
          
          <Card className="border-2 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
            <CardHeader className="bg-muted/50">
              <Tabs value={activeDemo} onValueChange={setActiveDemo}>
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="symbols">Symbol Extraction</TabsTrigger>
                  <TabsTrigger value="context">Smart Context</TabsTrigger>
                  <TabsTrigger value="deps">Dependency Docs</TabsTrigger>
                  <TabsTrigger value="research">Deep Research</TabsTrigger>
                </TabsList>
              </Tabs>
            </CardHeader>
            <CardContent className="p-0">
              <Tabs value={activeDemo}>
                <TabsContent value="symbols" className="p-6">
                  <div className="border border-gray-600 bg-black p-4 font-mono text-sm text-white rounded-lg">
                    <div className="absolute -top-6 left-0 text-gray-400 text-xs font-mono">● ● ●</div>
                    <div className="mb-2 text-gray-500 terminal-prompt">Extracting symbols from repository...</div>
                    <div>⚡ Cache hit: 94% (142/151 files)</div>
                    <div>📦 Found 841 functions, 156 classes, 89 interfaces</div>
                    <div>🔗 Mapped 2,341 import relationships</div>
                    <div className="mt-2 text-yellow-400">→ Processing 9 changed files...</div>
                    <div className="mt-1 text-blue-400">✓ Symbol extraction complete in 124ms</div>
                    <div className="mt-2 text-green-400">→ Incremental caching makes it lightning fast!</div>
                  </div>
                </TabsContent>
                
                <TabsContent value="context" className="p-6">
                  <div className="border border-gray-600 bg-black p-4 font-mono text-sm text-white rounded-lg">
                    <div className="absolute -top-6 left-0 text-gray-400 text-xs font-mono">● ● ●</div>
                    <div className="mb-2 text-gray-500 terminal-prompt">Building context for: "Add authentication"</div>
                    <div>📁 Analyzing repository structure...</div>
                    <div>🔍 Found existing auth patterns in 3 files</div>
                    <div>📚 Loading FastAPI security docs...</div>
                    <div>💡 Found 6 relevant examples on GitHub</div>
                    <div>📝 Retrieved 4 implementation guides</div>
                    <div className="mt-2 text-blue-400">
                      ✓ Context ready: 12 files, 8 docs, 6 examples
                    </div>
                  </div>
                </TabsContent>
                
                <TabsContent value="deps" className="p-6">
                  <div className="border border-gray-600 bg-black p-4 font-mono text-sm rounded-lg">
                    <div className="absolute -top-6 left-0 text-gray-400 text-xs font-mono">● ● ●</div>
                    <div className="mb-2 text-gray-500 terminal-prompt">Indexing dependency documentation...</div>
                    <div className="text-white">📦 Found 12 dependencies in pyproject.toml</div>
                    <div className="text-white">📚 Fetching documentation:</div>
                    <div className="text-blue-400 ml-4">• FastAPI: Official docs + 127 examples</div>
                    <div className="text-blue-400 ml-4">• SQLAlchemy: Core docs + ORM patterns</div>
                    <div className="text-blue-400 ml-4">• Pydantic: Validation + serialization guides</div>
                    <div className="text-yellow-400 mt-2">→ Building searchable vector index...</div>
                    <div className="text-white">✓ 8,421 documentation chunks indexed</div>
                  </div>
                </TabsContent>
                
                <TabsContent value="research" className="p-6">
                  <div className="border border-gray-600 bg-black p-4 font-mono text-sm text-white rounded-lg">
                    <div className="absolute -top-6 left-0 text-gray-400 text-xs font-mono">● ● ●</div>
                    <div className="mb-2 text-gray-500 terminal-prompt">Deep Research: FastAPI OAuth2 (Tier: Advanced)</div>
                    <div>🔍 Iteration 1: Initial survey of documentation...</div>
                    <div>📚 Iteration 3: Found OAuth2 patterns in 12 sources</div>
                    <div>🤔 Iteration 5: Resolving token storage contradiction</div>
                    <div>💡 Iteration 8: Deep dive into refresh tokens</div>
                    <div>✅ Iteration 12: Synthesis complete</div>
                    <div className="mt-2 text-green-400">→ Report: 47 sources, 94% confidence</div>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Available Tools */}
      <section className="container px-4 py-12 neo-section">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold">Context-Building Tools</h2>
            <p className="mt-3 text-lg text-muted-foreground">
              Powered by kit's production-grade code intelligence, already used at application-scale.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tools.map((tool, i) => (
              <div key={i} className="flex items-center space-x-3 p-4 border-2 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                <FileCode2 className="h-5 w-5 text-primary flex-shrink-0" />
                <div>
                  <code className="font-mono text-sm font-semibold text-primary">{tool.name}</code>
                  <p className="text-sm text-muted-foreground">{tool.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Comparison */}
      <section className="container px-4 py-12 neo-section">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold">Why use kit-mcp-dev</h2>
            <p className="mt-3 text-lg text-muted-foreground">
              The most comprehensive MCP server for coding with AI agents. It's also free and open source.
            </p>
          </div>
          
          <Card className="border-2 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            <CardContent className="p-8">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div>
                  <h3 className="font-semibold text-lg mb-4 flex items-center">
                    <Terminal className="h-5 w-5 mr-2 text-primary" />
                    kit-dev for mcp
                  </h3>
                  <ul className="space-y-2">
                    <li className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">Production-grade kit code analysis</span>
                    </li>
                    <li className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">Fast incremental caching</span>
                    </li>
                    <li className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">Multi-source documentation aggregation</span>
                    </li>
                    <li className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">Smart, task-aware context building</span>
                    </li>
                    <li className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">Semantic search with AI embeddings</span>
                    </li>
                    <li className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">Always up-to-date repository state</span>
                    </li>
                  </ul>
                </div>
                
                <div>
                  <h3 className="font-semibold text-lg mb-4 text-muted-foreground">Closed source toys</h3>
                  <ul className="space-y-2 text-muted-foreground">
                    <li className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-gray-400 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">Repository indexing</span>
                    </li>
                    <li className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-gray-400 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">Basic doc search</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-sm ml-7">No file tree navigation</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-sm ml-7">No semantic search</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-sm ml-7">No multi-source docs aggregation</span>
                    </li>
                  </ul>
                </div>
                
                <div>
                  <h3 className="font-semibold text-lg mb-4 text-muted-foreground">Just defaults</h3>
                  <ul className="space-y-2 text-muted-foreground">
                    <li className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-gray-400 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">Basic file operations</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-sm ml-7">Default repository intelligence</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-sm ml-7">Manual context gathering</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-sm ml-7">Outdated documentation</span>
                    </li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container px-4 py-16">
        <div className="mx-auto max-w-4xl text-center">
          <Card className="bg-gradient-to-r from-red-600 to-blue-600 text-white border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            <CardContent className="p-12">
              <h2 className="text-3xl font-bold mb-4">
                Get better context for free
              </h2>
              <p className="text-lg mb-8 text-blue-100">
                Don't pay a cent (besides tokens) for the <Link href="https://cased.com/blog/2025-06-13-kit/" className="text-white underline hover:text-blue-100">necessary building blocks</Link> of developer tools.
              </p>
              <div className="border border-gray-600 bg-black p-4 font-mono text-sm mb-8 text-left max-w-2xl mx-auto rounded-lg">
                <div className="text-white text-sm space-y-2">
                  <div>uvx --from cased-kit kit-mcp-dev</div>
                  <div className="text-gray-500"># Or with all extras (quote for zsh): uvx --from 'cased-kit[all]' kit-mcp-dev</div>
                  <div className="text-gray-500"># Add to Cursor settings.json:</div>
                  <div className="text-blue-400">"mcp.servers.kit-dev": {"{"}"command": "uvx", "args": ["--from", "cased-kit", "kit-mcp-dev"]{"}"}</div>
                </div>
              </div>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button size="lg" className="neo-button bg-white text-black" variant="secondary" asChild>
                  <Link href="/docs/quickstart">
                    Get Started Now
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                <Button size="lg" className="neo-button bg-white/10 hover:bg-white/20 text-white border-2 border-white" variant="outline" asChild>
                  <Link href="/docs">
                    Read Documentation
                    <BookOpen className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t">
        <div className="container px-4 py-8">
          <div className="flex flex-col sm:flex-row justify-between items-center">
            <div className="flex items-center space-x-2">
              <Terminal className="h-5 w-5 text-red-500" />
              <span className="font-semibold">kit-dev for mcp</span>
              <span className="text-muted-foreground">by Cased</span>
            </div>
            <div className="flex items-center space-x-6 mt-4 sm:mt-0">
              <Link href="https://github.com/cased/kit" className="text-muted-foreground hover:text-foreground">
                GitHub
              </Link>
              <Link href="/docs" className="text-muted-foreground hover:text-foreground">
                Docs
              </Link>
              <Link href="/tools" className="text-muted-foreground hover:text-foreground">
                Tools
              </Link>
              <span className="text-muted-foreground">MIT License</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
