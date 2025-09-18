"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Search,
  BookOpen,
  FileCode2,
  GitBranch,
  Code2
} from "lucide-react";

const tools = [
  {
    category: "Documentation Research",
    icon: <BookOpen className="h-5 w-5" />,
    tools: [
      {
        name: "deep_research_package",
        description: "Get comprehensive package documentation using multiple sources (Chroma + Context7)",
        parameters: ["package_name", "query"],
        naturalLanguage: "Using Kit, research the documentation for React hooks",
        example: `deep_research_package({
  "package_name": "react",
  "query": "How do hooks work?"  // optional specific question
})`
      }
    ]
  },
  {
    category: "Package Search (Chroma)",
    icon: <Search className="h-5 w-5" />,
    tools: [
      {
        name: "package_search_grep",
        description: "Use regex pattern matching to retrieve lines from package source code",
        parameters: ["package", "pattern", "max_results", "file_pattern", "case_sensitive"],
        naturalLanguage: "Using Kit, search for async functions in FastAPI source code",
        example: `package_search_grep({
  "package": "fastapi",
  "pattern": "async def \\\\w+",
  "max_results": 20,
  "file_pattern": "*.py",  // optional
  "case_sensitive": true  // optional
})`
      },
      {
        name: "package_search_hybrid",
        description: "Semantic search with optional regex filtering for intelligent code exploration",
        parameters: ["package", "query", "regex_filter", "max_results", "file_pattern"],
        naturalLanguage: "Using Kit, find authentication code in Django",
        example: `package_search_hybrid({
  "package": "django",
  "query": "user authentication and session management",
  "regex_filter": "@login_required",  // optional
  "max_results": 15
})`
      },
      {
        name: "package_search_read_file",
        description: "Read specific lines from a file in a code package",
        parameters: ["package", "file_path", "start_line", "end_line"],
        naturalLanguage: "Using Kit, read the models.py file from requests package",
        example: `package_search_read_file({
  "package": "requests",
  "file_path": "requests/models.py",
  "start_line": 100,  // optional
  "end_line": 200  // optional
})`
      }
    ]
  },
  {
    category: "Repository Management",
    icon: <FileCode2 className="h-5 w-5" />,
    tools: [
      {
        name: "open_repository",
        description: "Open a local directory or GitHub repository for analysis",
        parameters: ["path_or_url", "github_token", "ref"],
        naturalLanguage: "Using Kit, open the repository at /path/to/project",
        example: `open_repository({
  "path_or_url": "/Users/me/project",
  "github_token": "ghp_...",  // optional
  "ref": "main"  // optional
})`
      },
      {
        name: "get_file_tree",
        description: "Get the complete file structure of the repository",
        parameters: ["repo_id"],
        naturalLanguage: "Using Kit, show me the file tree of this repository",
        example: `get_file_tree({
  "repo_id": "repo_123"
})`
      }
    ]
  },
  {
    category: "Code Intelligence",
    icon: <Code2 className="h-5 w-5" />,
    tools: [
      {
        name: "extract_symbols",
        description: "Extract functions, classes, and other symbols from code",
        parameters: ["repo_id", "file_path", "symbol_type"],
        naturalLanguage: "Using Kit, extract all symbols from the main.py file",
        example: `extract_symbols({
  "repo_id": "repo_123",
  "file_path": "src/main.py",
  "symbol_type": "function"  // optional: function, class
})`
      },
      {
        name: "find_symbol_usages",
        description: "Find where a symbol is used throughout the codebase",
        parameters: ["repo_id", "symbol_name", "file_path"],
        naturalLanguage: "Using Kit, find all usages of the Database class",
        example: `find_symbol_usages({
  "repo_id": "repo_123",
  "symbol_name": "Database",
  "file_path": "src/"  // optional: narrow search
})`
      }
    ]
  },
  {
    category: "Code Search",
    icon: <Search className="h-5 w-5" />,
    tools: [
      {
        name: "grep_code",
        description: "Advanced regex search with context lines",
        parameters: ["repo_id", "pattern", "path", "context_lines"],
        naturalLanguage: "Using Kit, grep for import statements with context",
        example: `grep_code({
  "repo_id": "repo_123",
  "pattern": "^import .*",
  "path": "src/",
  "context_lines": 2
})`
      },
      {
        name: "grep_ast",
        description: "Search code using AST patterns for semantic code structure matching",
        parameters: ["repo_id", "pattern", "mode", "file_pattern", "max_results"],
        naturalLanguage: "Using Kit, find all async functions in the codebase",
        example: `grep_ast({
  "repo_id": "repo_123",
  "pattern": "async def",  // or '{"type": "try_statement"}'
  "mode": "simple",  // simple, pattern, or query
  "file_pattern": "**/*.py",
  "max_results": 20
})`
      }
    ]
  },
  {
    category: "Git Information",
    icon: <GitBranch className="h-5 w-5" />,
    tools: [
      {
        name: "review_diff",
        description: "Review code changes with AI-powered analysis",
        parameters: ["repo_id", "diff_spec", "priority_filter", "max_files", "model"],
        naturalLanguage: "Using Kit, review the diff between main and feature branch",
        example: `review_diff({
  "repo_id": "repo_123",
  "diff_spec": "main..feature-branch",
  "priority_filter": ["high", "medium"],  // optional
  "max_files": 10,  // optional limit
  "model": "gpt-4"  // optional
})`
      }
    ]
  }
];

export default function ToolsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");

  const filteredTools = tools
    .map(category => ({
      ...category,
      tools: category.tools.filter(tool =>
        tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tool.description.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }))
    .filter(category => 
      selectedCategory === "all" || 
      category.category === selectedCategory
    )
    .filter(category => category.tools.length > 0);

  return (
    <div className="prose prose-slate max-w-none">
      {/* Header */}
      <div className="not-prose mb-8">
        <h1 className="text-4xl font-bold mb-4">Available Tools</h1>
        <p className="text-xl text-muted-foreground mb-4">
          Explore all the powerful tools available to your AI assistant
        </p>

        {/* Philosophy Note */}
        <Card className="mt-6 border-2 border-blue-500 bg-blue-50 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <Code2 className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-blue-900">Focused Toolset Philosophy</h3>
                <p className="text-sm text-blue-800 mt-1">
                  We maintain a deliberately tight set of tools, focusing on kit's unique strengths rather than
                  duplicating what AI assistants already do well. We enhance existing tools with new features
                  instead of adding redundant ones. This keeps context clean and responses fast.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filter */}
      <div className="not-prose mb-8">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search tools..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 neo-input"
            />
          </div>
          <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
            <TabsList className="grid grid-cols-3 lg:grid-cols-6 w-full bg-white">
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="Documentation Research">Docs</TabsTrigger>
              <TabsTrigger value="Repository Management">Repo</TabsTrigger>
              <TabsTrigger value="Code Intelligence">Intel</TabsTrigger>
              <TabsTrigger value="Code Search">Search</TabsTrigger>
              <TabsTrigger value="Git Information">Git</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {/* Tools Grid */}
      <div className="not-prose">
        {filteredTools.length === 0 ? (
          <Card className="border-2 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            <CardContent className="p-12 text-center">
              <p className="text-muted-foreground">No tools found matching your search.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-8">
            {filteredTools.map((category, i) => (
              <div key={i}>
                <div className="flex items-center space-x-2 mb-4">
                  <div className="p-2 bg-primary/10 rounded-lg text-primary">
                    {category.icon}
                  </div>
                  <h2 className="text-2xl font-bold">{category.category}</h2>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {category.tools.map((tool, j) => (
                    <Card key={j} className="border-2 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                      <CardHeader>
                        <CardTitle className="font-mono text-lg">{tool.name}</CardTitle>
                        <CardDescription>{tool.description}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          {tool.naturalLanguage && (
                            <div>
                              <h4 className="text-sm font-semibold mb-1">Natural Language</h4>
                              <p className="text-sm text-muted-foreground italic">
                                "{tool.naturalLanguage}"
                              </p>
                            </div>
                          )}
                          <div>
                            <h4 className="text-sm font-semibold mb-1">Parameters</h4>
                            <div className="flex flex-wrap gap-1">
                              {tool.parameters.map((param, k) => (
                                <Badge key={k} variant="secondary" className="text-xs neo-badge bg-blue-200 text-black">
                                  {param}
                                </Badge>
                              ))}
                            </div>
                          </div>
                          <div>
                            <h4 className="text-sm font-semibold mb-1">Function Signature</h4>
                            <pre className="border-2 border-black bg-black text-white p-3 text-xs overflow-x-auto">
                              <code>{tool.example}</code>
                            </pre>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}