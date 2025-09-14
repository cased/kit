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
  RefreshCw,
  Code2
} from "lucide-react";

const tools = [
  {
    category: "Documentation Research",
    icon: <BookOpen className="h-5 w-5" />,
    tools: [
      {
        name: "deep_research_package",
        description: "Get comprehensive package documentation using LLM knowledge",
        parameters: ["package_name", "query"],
        naturalLanguage: "Using Kit, research the documentation for React hooks",
        example: `deep_research_package({
  "package_name": "react",
  "query": "How do hooks work?"  // optional specific question
})`
      },
      {
        name: "build_smart_context",
        description: "Build comprehensive context for a development task from multiple sources",
        parameters: ["repo_id", "task_description", "include_tests", "include_docs", "include_dependencies", "max_files"],
        naturalLanguage: "Using Kit, build context for implementing a new authentication feature",
        example: `build_smart_context({
  "repo_id": "repo_123",
  "task_description": "implement OAuth2 authentication",
  "include_tests": true,
  "include_docs": true,
  "include_dependencies": true,
  "max_files": 20
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
      },
      {
        name: "get_file_content",
        description: "Read a single file from the repository",
        parameters: ["repo_id", "file_path"],
        naturalLanguage: "Using Kit, read the main.py file",
        example: `get_file_content({
  "repo_id": "repo_123",
  "file_path": "src/main.py"
})`
      },
      {
        name: "get_multiple_file_contents",
        description: "Read multiple files in a single efficient operation",
        parameters: ["repo_id", "file_paths"],
        naturalLanguage: "Using Kit, read main.py, utils.py, and config.py",
        example: `get_multiple_file_contents({
  "repo_id": "repo_123",
  "file_paths": ["main.py", "utils.py", "config.py"]
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
      },
      {
        name: "get_code_summary",
        description: "Get an AI-generated summary of code",
        parameters: ["repo_id", "file_path", "symbol_name"],
        naturalLanguage: "Using Kit, summarize the authentication module",
        example: `get_code_summary({
  "repo_id": "repo_123",
  "file_path": "src/auth.py",
  "symbol_name": "authenticate"  // optional
})`
      }
    ]
  },
  {
    category: "Code Search",
    icon: <Search className="h-5 w-5" />,
    tools: [
      {
        name: "search_code",
        description: "Search for text patterns across the codebase",
        parameters: ["repo_id", "query", "pattern"],
        naturalLanguage: "Using Kit, search for all TODO comments in Python files",
        example: `search_code({
  "repo_id": "repo_123",
  "query": "TODO",
  "pattern": "*.py"  // optional file pattern
})`
      },
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
        name: "get_git_info",
        description: "Get Git metadata about the repository",
        parameters: ["repo_id"],
        naturalLanguage: "Using Kit, show me the git info for this repository",
        example: `get_git_info({
  "repo_id": "repo_123"
})`
      },
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
  },
  {
    category: "Local Development",
    icon: <RefreshCw className="h-5 w-5" />,
    tools: [
      {
        name: "watch_files",
        description: "Watch files for real-time changes and get notifications",
        parameters: ["repo_id", "patterns", "exclude_dirs"],
        naturalLanguage: "Using Kit, watch Python and JavaScript files for changes",
        example: `watch_files({
  "repo_id": "repo_123",
  "patterns": ["*.py", "*.js", "*.ts"],
  "exclude_dirs": [".git", "node_modules"]
})`
      },
      {
        name: "get_file_changes",
        description: "Get recent file changes from the file watcher",
        parameters: ["repo_id", "limit"],
        naturalLanguage: "Using Kit, show me the last 10 file changes",
        example: `get_file_changes({
  "repo_id": "repo_123",
  "limit": 10
})`
      }
    ]
  },
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
        <p className="text-xl text-muted-foreground mb-8">
          Explore all the powerful tools available to your AI assistant
        </p>
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
            <TabsList className="grid grid-cols-4 lg:grid-cols-7 w-full">
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="Documentation Research">Docs</TabsTrigger>
              <TabsTrigger value="Repository Management">Repo</TabsTrigger>
              <TabsTrigger value="Code Intelligence">Intel</TabsTrigger>
              <TabsTrigger value="Code Search">Search</TabsTrigger>
              <TabsTrigger value="Git Information">Git</TabsTrigger>
              <TabsTrigger value="Local Development">Local</TabsTrigger>
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