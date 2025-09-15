import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Zap, Code2, Activity } from "lucide-react";

export default function SearchPage() {
  return (
    <div className="prose prose-slate max-w-none px-4 sm:px-0">
      <div className="not-prose mb-8">
        <Badge variant="secondary" className="neo-badge bg-yellow-300 text-black mb-4">
          Core Feature
        </Badge>
        <h1 className="text-2xl sm:text-4xl font-bold mb-4">Code Search</h1>
        <p className="text-sm sm:text-xl text-muted-foreground">
          Powerful text search and AST-based code pattern matching
        </p>
      </div>

      <div className="my-8">
        <h2 className="text-xl sm:text-2xl font-bold mb-4">Overview</h2>
        <p className="text-sm sm:text-base text-muted-foreground mb-6">
          kit-dev-mcp provides two powerful search capabilities: fast literal string search with grep,
          and AST-based pattern matching for finding code by structure using tree-sitter.
        </p>
      </div>

      <Card className="my-8 neo-card border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
        <CardHeader>
          <CardTitle>Search Tools</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h4 className="font-mono text-red-600 font-semibold">grep_code</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Fast literal string search with context lines
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-2 sm:p-4 font-mono text-xs sm:text-sm mt-2">
                <code className="text-white">
                  grep_code(repo_id="...", pattern="TODO", context_lines=2)
                </code>
              </div>
            </div>
            
            <div>
              <h4 className="font-mono text-red-600 font-semibold">grep_ast</h4>
              <p className="text-sm text-muted-foreground mt-1">
                AST-based search to find code by structure (functions, classes, try blocks, etc.)
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-2 sm:p-4 font-mono text-xs sm:text-sm mt-2">
                <code className="text-white">
                  grep_ast(repo_id="...", pattern="async def", mode="simple", max_results=20)
                </code>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="my-8">
        <h2 className="text-xl sm:text-2xl font-bold mb-4">Text Search Features</h2>
        <Card className="neo-card border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
          <CardContent className="p-4 sm:p-6">
            <div className="flex items-start mb-4">
              <Zap className="h-5 w-5 text-red-500 mr-2 mt-0.5" />
              <div>
                <h3 className="font-semibold">Regex Support</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Full regular expression support for complex pattern matching
                </p>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div className="border-2 border-black bg-black rounded-lg p-2 sm:p-4 font-mono text-xs sm:text-sm">
                <div className="text-xs text-gray-500 mb-1">Find all function definitions:</div>
                <code className="text-white">
                  pattern="^def\s+\w+\("
                </code>
              </div>
              <div className="border-2 border-black bg-black rounded-lg p-2 sm:p-4 font-mono text-xs sm:text-sm">
                <div className="text-xs text-gray-500 mb-1">Find imports:</div>
                <code className="text-white">
                  pattern="^import|^from.*import"
                </code>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-xl sm:text-2xl font-bold mb-4">AST Pattern Search (grep_ast)</h2>
        <Card className="neo-card border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
          <CardContent className="p-4 sm:p-6">
            <div className="flex items-start mb-4">
              <Activity className="h-5 w-5 text-blue-500 mr-2 mt-0.5" />
              <div>
                <h3 className="font-semibold">Structure-Based Search</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Find code by its structure using Abstract Syntax Tree patterns
                </p>
              </div>
            </div>
            
            <div className="mt-4 p-3 bg-muted/50 rounded">
              <p className="text-xs sm:text-sm text-muted-foreground">
                <strong>How it works:</strong> AST search uses tree-sitter to parse code and match 
                structural patterns. For example, searching for "async def" will find all async 
                functions, "class $NAME(BaseModel)" finds classes extending BaseModel, or 
                {`{"type": "try_statement"}`} finds all try blocks.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-xl sm:text-2xl font-bold mb-4">Usage Examples</h2>
        <Tabs defaultValue="grep" className="w-full">
          <TabsList className="grid grid-cols-2 w-full">
            <TabsTrigger value="grep" className="text-xs sm:text-sm">Grep Search</TabsTrigger>
            <TabsTrigger value="ast" className="text-xs sm:text-sm">AST Search</TabsTrigger>
          </TabsList>

          <TabsContent value="grep">
            <Card className="neo-card border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardContent className="p-4">
                <h4 className="font-semibold mb-2">Find TODO comments with context</h4>
                <div className="border-2 border-black bg-black rounded-lg p-2 sm:p-4 font-mono text-xs sm:text-sm">
                  <pre className="text-white">
                    <code>{`# Ask your AI:
"Find all TODO comments with surrounding context"

# AI executes:
grep_code(
  repo_id="...",
  pattern="TODO",
  context_lines=3,
  case_sensitive=false
)`}</code>
                  </pre>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="ast">
            <Card className="neo-card border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardContent className="p-4">
                <h4 className="font-semibold mb-2">Find async functions</h4>
                <div className="border-2 border-black bg-black rounded-lg p-2 sm:p-4 font-mono text-xs sm:text-sm">
                  <pre className="text-white">
                    <code>{`# Ask your AI:
"Find all async functions in the codebase"

# AI executes:
grep_ast(
  repo_id="...",
  pattern="async def",
  mode="simple",
  file_pattern="**/*.py",
  max_results=20
)`}</code>
                  </pre>
                </div>
              </CardContent>
            </Card>
            
            <Card className="mt-4 neo-card border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardContent className="p-4">
                <h4 className="font-semibold mb-2">Find error handling blocks</h4>
                <div className="border-2 border-black bg-black rounded-lg p-2 sm:p-4 font-mono text-xs sm:text-sm">
                  <pre className="text-white">
                    <code>{`# Ask your AI:
"Show me all try-except blocks"

# AI executes:
grep_ast(
  repo_id="...",
  pattern='{"type": "try_statement"}',
  mode="pattern",
  max_results=20
)`}</code>
                  </pre>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}