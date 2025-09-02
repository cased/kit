import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Copy, CheckCircle, Terminal, Sparkles } from "lucide-react";

export default function SystemPromptsPage() {
  return (
    <div className="prose prose-slate max-w-none">
      <div className="not-prose mb-8">
        <Badge variant="secondary" className="neo-badge bg-yellow-300 text-black mb-4">
          Power User Guide
        </Badge>
        <h1 className="text-4xl font-bold mb-4">Optimizing Your AI with System Prompts</h1>
        <p className="text-xl text-muted-foreground">
          Configure your AI assistant to automatically leverage Kit's powerful tools for better code understanding
        </p>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Why System Prompts Matter</h2>
        <p className="text-muted-foreground mb-6">
          System prompts guide your AI assistant's behavior. By adding Kit-specific instructions, you ensure your AI 
          automatically uses the right tools for code analysis, documentation research, and context building - 
          resulting in more accurate and helpful responses.
        </p>
      </div>

      <Card className="neo-card my-8">
        <CardHeader>
          <CardTitle>Recommended System Prompts</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="claude" className="w-full">
            <TabsList>
              <TabsTrigger value="claude">Claude</TabsTrigger>
              <TabsTrigger value="cursor">Cursor</TabsTrigger>
              <TabsTrigger value="custom">Custom AI</TabsTrigger>
            </TabsList>
            
            <TabsContent value="claude">
              <div className="space-y-4">
                <h4 className="font-semibold">For Claude Desktop/Web</h4>
                <p className="text-sm text-muted-foreground mb-2">
                  Add this to your project's instructions or conversation context:
                </p>
                <Card className="neo-card border-2 border-black bg-black p-4">
                  <pre className="text-red-400 text-sm overflow-x-auto">
                    <code>{`# Kit MCP Usage Guidelines

When working with code in this project, always:

1. **Start with Repository Context**
   - Use \`open_repository\` to load the codebase
   - Use \`get_file_tree\` to understand structure
   - Use \`extract_symbols\` for fast analysis

2. **For Code Understanding**
   - Use \`search_text\` for finding implementations
   - Use \`find_symbol_usages\` to track usage
   - Use \`get_dependency_graph\` to understand relationships

3. **For Documentation**
   - Use \`deep_research_package\` for package docs
   - Use \`context7_research\` for AI-aggregated docs
   - Use \`build_smart_context\` before implementing features

4. **Best Practices**
   - Always gather context before making suggestions
   - Use incremental symbol extraction (it's cached!)
   - Research dependencies before using new packages
   - Build smart context for complex tasks

Remember: Better context = Better code suggestions`}</code>
                  </pre>
                </Card>
              </div>
            </TabsContent>
            
            <TabsContent value="cursor">
              <div className="space-y-4">
                <h4 className="font-semibold">For Cursor IDE</h4>
                <p className="text-sm text-muted-foreground mb-2">
                  Add to your .cursorrules file in your project root:
                </p>
                <Card className="neo-card border-2 border-black bg-black p-4">
                  <pre className="text-red-400 text-sm overflow-x-auto">
                    <code>{`# .cursorrules - Kit MCP Integration

## Available MCP Tools
You have access to kit-mcp-dev with these tools:
- open_repository: Load codebases
- get_file_tree: Navigate structure  
- extract_symbols: Fast symbol extraction
- search_text: Regex search
- find_symbol_usages: Track usage
- get_dependency_graph: Import maps
- deep_research_package: Multi-source docs
- context7_research: AI-aggregated docs
- build_smart_context: Task-aware context

## Tool Usage Rules
1. ALWAYS use get_file_tree before suggesting file changes
2. ALWAYS use extract_symbols for understanding code
3. ALWAYS use deep_research_package before using new libraries
4. ALWAYS use build_smart_context for feature implementation

## Context Building Workflow
For any code task:
1. Open repository
2. Get file tree
3. Extract symbols (cached - very fast!)
4. Research relevant packages
5. Build smart context
6. Then provide solution

This ensures accurate, context-aware suggestions.`}</code>
                  </pre>
                </Card>
              </div>
            </TabsContent>
            
            <TabsContent value="custom">
              <div className="space-y-4">
                <h4 className="font-semibold">For Any AI Assistant</h4>
                <p className="text-sm text-muted-foreground mb-2">
                  Generic prompt that works with any AI that supports MCP:
                </p>
                <Card className="neo-card border-2 border-black bg-black p-4">
                  <pre className="text-red-400 text-sm overflow-x-auto">
                    <code>{`You have access to kit-mcp-dev server with powerful code intelligence tools.

MANDATORY WORKFLOW for code tasks:
1. open_repository(path) - Load the codebase
2. get_file_tree() - Understand structure
3. extract_symbols() - Analyze code (cached)
4. For new libraries: deep_research_package() or context7_research()
5. build_smart_context(task) - Gather all relevant info

TOOL DESCRIPTIONS:
- open_repository: Opens local/remote repositories
- get_file_tree: Shows project structure
- extract_symbols: Fast symbol extraction with caching
- get_file_content_multi: Read multiple files at once
- search_text: Powerful regex search
- find_symbol_usages: Find where symbols are used
- get_dependency_graph: Map import relationships
- deep_research_package: Research from multiple doc sources
- context7_research: AI-aggregated documentation
- build_smart_context: Intelligent context for tasks

Always use these tools proactively. Don't wait to be asked.
Better context = Better code.`}</code>
                  </pre>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Automated Setup Script</h2>
        <p className="text-muted-foreground mb-4">
          Run this script to automatically add Kit optimization to your project:
        </p>
        <Card className="neo-card">
          <CardContent className="p-4">
            <pre className="border-2 border-black bg-black text-white p-4 rounded-lg text-sm overflow-x-auto">
              <code>{`#!/bin/bash
# kit-optimize.sh - Add Kit MCP prompts to your project

cat > .kit-prompts.md << 'EOF'
# Kit MCP Usage for This Project

When working with code, ALWAYS:
1. Use Kit to open and analyze the codebase
2. Use Kit to explore the file structure  
3. Use Kit to extract and analyze code symbols
4. Use Kit to research package documentation
5. Use Kit to build context before implementing

Available tools:
- Repository: open_repository, get_file_tree
- Analysis: extract_symbols, find_symbol_usages
- Search: search_text, get_dependency_graph
- Docs: deep_research_package, context7_research
- Context: build_smart_context
EOF

echo "✅ Created .kit-prompts.md"
echo "📝 Include this file in your AI conversations for better results!"`}</code>
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}