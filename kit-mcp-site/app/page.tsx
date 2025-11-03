"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Terminal,
  Shield,
  GitBranch,
  Eye,
  Search,
  BookOpen,
  Sparkles,
  ArrowRight,
  CheckCircle,
  Github,
  FileCode2,
  FileText,
  Activity,
  Lock,
  RefreshCw,
  Layers,
  Package
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export default function Home() {
  const [activeDemo, setActiveDemo] = useState("symbols");
  
  // Create the Cursor deep link config
  const cursorConfig = {
    "kit-dev-mcp": {
      "command": "uvx",
      "args": ["--from", "cased-kit", "kit-dev-mcp"]
    }
  };
  const encodedConfig = typeof window !== 'undefined' 
    ? btoa(JSON.stringify(cursorConfig))
    : '';
  const cursorDeepLink = `cursor://settings/mcp/install?server=${encodeURIComponent(encodedConfig)}`;

  const features = [
    {
      icon: <Layers className="h-5 w-5" />,
      title: "Production-Grade Code Intelligence",
      description: "kit's battle-tested repository analysis, symbol extraction, and dependency mapping"
    },
    {
      icon: <BookOpen className="h-5 w-5" />,
      title: "Deep Documentation Research",
      description: "Multi-source documentation with Chroma Package Search + Context7. Get source code and docs in one query."
    },
    {
      icon: <Package className="h-5 w-5" />,
      title: "Chroma Package Search",
      description: "Search source code of popular packages with regex patterns, semantic search, and file reading"
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
      title: "AST-Based Pattern Matching",
      description: "Find code by structure using tree-sitter - search for async functions, error handlers, and more"
    },
    {
      icon: <BookOpen className="h-5 w-5" />,
      title: "Local LLM Documentation",
      description: "Support for local LLMs like Ollama - keep your documentation research private and free"
    }
  ];

  const tools = [
    { name: "open_repository", description: "Open local and remote repositories" },
    { name: "deep_research_package", description: "Multi-source package docs (Chroma + Context7)" },
    { name: "package_search_grep", description: "Regex search in package source code" },
    { name: "package_search_hybrid", description: "Semantic search with optional regex" },
    { name: "package_search_read_file", description: "Read files from packages" },
    { name: "get_file_tree", description: "Structured file navigation" },
    { name: "extract_symbols", description: "Fast symbol extraction with caching" },
    { name: "grep_code", description: "Fast literal search with smart filtering" },
    { name: "grep_ast", description: "AST-based pattern matching with tree-sitter" },
    { name: "find_symbol_usages", description: "Track symbol usage everywhere" },
    { name: "review_diff", description: "AI-powered git diff review" }
  ];

  return (
    <div className="min-h-screen bg-white relative">
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
              <Link href="/docs/tools">Tools</Link>
            </Button>
            <Button variant="ghost" size="sm" className="px-2 sm:px-4 neo-button" asChild>
              <Link href="https://github.com/cased/kit" target="_blank">
                <Github className="h-4 w-4 sm:mr-2" />
                <span className="hidden sm:inline">GitHub</span>
              </Link>
            </Button>
            <Button size="sm" className="hidden sm:flex neo-button bg-red-500 hover:bg-red-600 text-white" asChild>
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
          <p className="mt-6 text-xl md:text-2xl text-muted-foreground">
            The best MCP server for coding with AI agents. MIT licensed from <Link href="https://cased.com" className="text-blue-500 hover:text-blue-600">Cased</Link>.
          </p>
          
          {/* Quick Install */}
          <div className="mt-6 mb-6 mx-auto max-w-2xl">
            <div className="border border-gray-600 bg-black p-3 font-mono text-sm rounded-lg">
              <div className="flex items-center justify-between">
                <code className="text-white text-xs sm:text-sm font-bold">
                  uvx --from "cased-kit{'>'}=2.0.0" kit-dev-mcp
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
            <Button size="lg" className="neo-button bg-blue-500 hover:bg-blue-600 text-white" asChild>  
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
                    <div className="p-2 bg-primary/10 rounded-lg text-primary flex-shrink-0 w-10 h-10 flex items-center justify-center">
                      {feature.icon}
                    </div>
                    <CardTitle className="text-base sm:text-lg">{feature.title}</CardTitle>
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

      {/* New Package Search Section */}
      <section className="container px-4 py-12 neo-section bg-gradient-to-br from-purple-50 to-blue-50">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-8">
            <Badge className="neo-badge bg-purple-500 text-white mb-4">NEW</Badge>
            <h2 className="text-3xl font-bold">Chroma Package Search Integration</h2>
            <p className="mt-3 text-lg text-muted-foreground">
              Search and explore source code from popular packages directly through MCP.
              Now integrated with deep_research_package for comprehensive multi-source documentation.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <Card className="border-2 border-purple-500 bg-white shadow-[4px_4px_0px_0px_rgba(147,51,234,1)]">
              <CardHeader>
                <div className="flex items-center space-x-3">
                  <Search className="h-5 w-5 text-purple-500" />
                  <CardTitle className="text-base">package_search_grep</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Regex pattern matching to find code patterns across package source files
                </p>
              </CardContent>
            </Card>

            <Card className="border-2 border-purple-500 bg-white shadow-[4px_4px_0px_0px_rgba(147,51,234,1)]">
              <CardHeader>
                <div className="flex items-center space-x-3">
                  <Sparkles className="h-5 w-5 text-purple-500" />
                  <CardTitle className="text-base">package_search_hybrid</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Semantic search with optional regex filtering for intelligent exploration
                </p>
              </CardContent>
            </Card>

            <Card className="border-2 border-purple-500 bg-white shadow-[4px_4px_0px_0px_rgba(147,51,234,1)]">
              <CardHeader>
                <div className="flex items-center space-x-3">
                  <FileText className="h-5 w-5 text-purple-500" />
                  <CardTitle className="text-base">package_search_read_file</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Read specific files or line ranges from package source code
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="flex justify-center">
            <Button size="lg" className="neo-button bg-purple-500 hover:bg-purple-600 text-white" asChild>
              <Link href="/docs/package-search">
                Explore Package Search
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* And a lot more section */}
      <section className="container px-4 py-12 neo-section bg-gradient-to-br from-blue-50 to-red-50">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold">Agentic DevOps from Cased</h2>
            <p className="mt-3 text-lg text-muted-foreground">
              kit is open source from <Link href="https://cased.com" className="text-blue-500 hover:text-blue-600">Cased</Link>. Cased provides AI agents that do DevOps for you, so you can focus on your product.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="border-2 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader>
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center">
                    <Activity className="h-6 w-6 text-blue-600" />
                  </div>
                  <CardTitle className="text-base sm:text-lg">Autonomous Deployments</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4">
                  AI agents that integrate with your CI/CD, catch issues before production, 
                  and handle automatic rollbacks. Stop managing deployments manually.
                </p>
                <Badge className="neo-badge bg-green-500 hover:bg-green-500 text-white">Zero-touch deploys</Badge>
              </CardContent>
            </Card>

            <Card className="border-2 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader>
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center">
                    <Shield className="h-6 w-6 text-red-600" />
                  </div>
                  <CardTitle className="text-base sm:text-lg">Infrastructure Agents</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4">
                  Continuous scanning for drift, security gaps, and compliance issues. 
                  Agents automatically implement fixes before problems escalate.
                </p>
                <Badge className="neo-badge bg-blue-500 hover:bg-blue-500 text-white">SOC2 compliant</Badge>
              </CardContent>
            </Card>

            <Card className="border-2 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader>
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center">
                    <GitBranch className="h-6 w-6 text-purple-600" />
                  </div>
                  <CardTitle className="text-base sm:text-lg">Cost Optimization Agents</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4">
                  AI agents that manage cloud costs and resource scaling. Integrates with Terraform 
                  to automatically adjust infrastructure based on actual usage.
                </p>
                <Badge className="neo-badge bg-purple-500 hover:bg-purple-500 text-white">30-50% cost reduction</Badge>
              </CardContent>
            </Card>

            <Card className="border-2 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader>
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center">
                    <RefreshCw className="h-6 w-6 text-green-600" />
                  </div>
                  <CardTitle className="text-base sm:text-lg">Agentic Workflows & API</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4">
                  Orchestrate agents with event-driven workflows. Multiple triggers, custom logic, 
                  and a full API for programmatic control of your DevOps automation.
                </p>
                <Badge className="neo-badge bg-yellow-500 hover:bg-yellow-500 text-black">Fully programmable</Badge>
              </CardContent>
            </Card>
          </div>

          <div className="mt-8 text-center">
            <Button size="lg" className="neo-button bg-blue-500 hover:bg-blue-600 text-white" asChild>
              <Link href="https://cased.com" target="_blank">
                Let AI Agents Do Your DevOps
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
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
                <TabsList className="grid w-full grid-cols-2 sm:grid-cols-4 gap-1">
                  <TabsTrigger value="symbols" className="text-xs sm:text-sm px-2">Symbols</TabsTrigger>
                  <TabsTrigger value="context" className="text-xs sm:text-sm px-2">Context</TabsTrigger>
                  <TabsTrigger value="deps" className="text-xs sm:text-sm px-2">Deps</TabsTrigger>
                  <TabsTrigger value="research" className="text-xs sm:text-sm px-2">Research</TabsTrigger>
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
                    <div className="mb-2 text-gray-500 terminal-prompt">Deep Research: FastAPI OAuth2</div>
                    <div>🔍 Searching official documentation...</div>
                    <div>📚 Found OAuth2 patterns in 12 sources</div>
                    <div>🤔 Analyzing implementation patterns</div>
                    <div>💡 Synthesizing best practices</div>
                    <div>✅ Research complete</div>
                    <div className="mt-2 text-green-400">→ Comprehensive report generated from 47 sources</div>
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
            <h2 className="text-3xl font-bold">Why use kit-dev-mcp</h2>
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
                      <span className="text-sm">AST-based code search with tree-sitter</span>
                    </li>
                    <li className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">Always up-to-date repository state</span>
                    </li>
                  </ul>
                </div>
                
                <div>
                  <h3 className="font-semibold text-lg mb-4 text-muted-foreground">Closed source alts</h3>
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
                      <span className="text-sm ml-7">No AST-based code search</span>
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
              <Link href="/docs/tools" className="text-muted-foreground hover:text-foreground">
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
