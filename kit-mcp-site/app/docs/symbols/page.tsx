import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Zap, Code2, FileCode2, Activity } from "lucide-react";

export default function SymbolsPage() {
  return (
    <div className="prose prose-slate max-w-none">
      <div className="not-prose mb-8">
        <Badge variant="secondary" className="neo-badge bg-yellow-300 text-black mb-4">
          Core Feature
        </Badge>
        <h1 className="text-4xl font-bold mb-4">Symbol Extraction</h1>
        <p className="text-xl text-muted-foreground">
          Fast, cached extraction of functions, classes, and other code symbols
        </p>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Overview</h2>
        <p className="text-muted-foreground mb-6">
          Symbol extraction is one of Kit's most powerful features. It identifies and extracts 
          functions, classes, methods, interfaces, and other code constructs from your repository. 
          With incremental caching, subsequent extractions are lightning fast.
        </p>
      </div>

      <Card className="neo-card my-8">
        <CardHeader>
          <CardTitle>Available Tools</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h4 className="font-mono-accent text-red-600 font-semibold">extract_symbols</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Fast symbol extraction with intelligent caching
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm mt-2">
                <code className="text-white text-xs">
                  extract_symbols(repo_id="...", file_path="main.py")
                </code>
              </div>
            </div>
            
            <div>
              <h4 className="font-mono-accent text-red-600 font-semibold">extract_symbols</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Standard symbol extraction (without caching)
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm mt-2">
                <code className="text-white text-xs">
                  extract_symbols(repo_id="...", file_path="src/")
                </code>
              </div>
            </div>
            
            <div>
              <h4 className="font-mono-accent text-red-600 font-semibold">find_symbol_usages</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Find where a symbol is used throughout the codebase
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm mt-2">
                <code className="text-white text-xs">
                  find_symbol_usages(repo_id="...", symbol_name="MyClass")
                </code>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Incremental Caching</h2>
        <Card className="neo-card border-red-500/20">
          <CardContent className="p-6">
            <div className="flex items-start mb-4">
              <Activity className="h-5 w-5 text-red-500 mr-2 mt-0.5" />
              <div>
                <h3 className="font-semibold">Lightning Fast Performance</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Kit's incremental caching system makes symbol extraction incredibly fast
                </p>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div className="bg-black rounded-lg p-4 font-mono text-sm">
                <div className="text-xs text-gray-500 mb-1">First extraction:</div>
                <code className="text-white text-xs">
                  Processing 150 files... (3.2s)
                </code>
              </div>
              <div className="bg-black rounded-lg p-4 font-mono text-sm">
                <div className="text-xs text-gray-500 mb-1">Subsequent extractions:</div>
                <code className="text-white text-xs">
                  Cache hit 95%! (124ms)
                </code>
              </div>
            </div>
            
            <div className="mt-4 p-3 bg-muted/50 rounded">
              <p className="text-xs text-muted-foreground">
                <strong>How it works:</strong> Kit tracks file modifications and only re-processes 
                changed files. The cache automatically invalidates when you switch branches, 
                commit, or modify files.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Extracted Symbol Types</h2>
        <Tabs defaultValue="python" className="w-full">
          <TabsList>
            <TabsTrigger value="python">Python</TabsTrigger>
            <TabsTrigger value="javascript">JavaScript/TypeScript</TabsTrigger>
            <TabsTrigger value="other">Other Languages</TabsTrigger>
          </TabsList>
          
          <TabsContent value="python">
            <Card className="neo-card">
              <CardContent className="p-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-semibold text-sm mb-2">Extracted:</h4>
                    <ul className="space-y-1 text-sm text-muted-foreground">
                      <li className="flex items-center">
                        <Code2 className="h-3 w-3 mr-2 text-red-500" />
                        Classes
                      </li>
                      <li className="flex items-center">
                        <Code2 className="h-3 w-3 mr-2 text-red-500" />
                        Functions
                      </li>
                      <li className="flex items-center">
                        <Code2 className="h-3 w-3 mr-2 text-red-500" />
                        Methods
                      </li>
                      <li className="flex items-center">
                        <Code2 className="h-3 w-3 mr-2 text-red-500" />
                        Decorators
                      </li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm mb-2">Example:</h4>
                    <div className="bg-black rounded-lg p-4 font-mono text-sm">
                      <pre className="text-white text-xs">
                        <code>{`{
  "name": "MyClass",
  "type": "class",
  "line": 15,
  "file": "main.py"
}`}</code>
                      </pre>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="javascript">
            <Card className="neo-card">
              <CardContent className="p-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-semibold text-sm mb-2">Extracted:</h4>
                    <ul className="space-y-1 text-sm text-muted-foreground">
                      <li className="flex items-center">
                        <Code2 className="h-3 w-3 mr-2 text-red-500" />
                        Classes
                      </li>
                      <li className="flex items-center">
                        <Code2 className="h-3 w-3 mr-2 text-red-500" />
                        Functions
                      </li>
                      <li className="flex items-center">
                        <Code2 className="h-3 w-3 mr-2 text-red-500" />
                        Interfaces (TS)
                      </li>
                      <li className="flex items-center">
                        <Code2 className="h-3 w-3 mr-2 text-red-500" />
                        React Components
                      </li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm mb-2">Example:</h4>
                    <div className="bg-black rounded-lg p-4 font-mono text-sm">
                      <pre className="text-white text-xs">
                        <code>{`{
  "name": "Button",
  "type": "component",
  "line": 8,
  "file": "Button.tsx"
}`}</code>
                      </pre>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="other">
            <Card className="neo-card">
              <CardContent className="p-6">
                <p className="text-sm text-muted-foreground mb-4">
                  Kit supports symbol extraction for many languages via Tree-sitter:
                </p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {["Go", "Rust", "Java", "C++", "Ruby", "PHP", "C#", "Swift", "Kotlin"].map(lang => (
                    <div key={lang} className="flex items-center text-sm">
                      <FileCode2 className="h-3 w-3 mr-2 text-red-500" />
                      {lang}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Usage Examples</h2>
        <div className="space-y-4">
          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="text-lg">Extract symbols from entire repository</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-black rounded-lg p-4 font-mono text-sm">
                <pre className="text-white text-sm">
                  <code>{`# Ask your AI:
"Extract all symbols from the repository"

# AI executes:
extract_symbols(repo_id="...")`}</code>
                </pre>
              </div>
            </CardContent>
          </Card>
          
          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="text-lg">Extract from specific file</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-black rounded-lg p-4 font-mono text-sm">
                <pre className="text-white text-sm">
                  <code>{`# Ask your AI:
"What functions are in main.py?"

# AI executes:
extract_symbols(
  repo_id="...",
  file_path="main.py"
)`}</code>
                </pre>
              </div>
            </CardContent>
          </Card>
          
          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="text-lg">Find symbol usage</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-black rounded-lg p-4 font-mono text-sm">
                <pre className="text-white text-sm">
                  <code>{`# Ask your AI:
"Where is the Database class used?"

# AI executes:
find_symbol_usages(
  repo_id="...",
  symbol_name="Database"
)`}</code>
                </pre>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Performance Tips</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="neo-card border-red-500/20">
            <CardContent className="p-4">
              <Zap className="h-4 w-4 text-red-500 mb-2" />
              <strong className="text-sm">Always use incremental</strong>
              <p className="text-xs text-muted-foreground mt-1">
                extract_symbols is much faster due to caching
              </p>
            </CardContent>
          </Card>
          <Card className="neo-card border-red-500/20">
            <CardContent className="p-4">
              <Zap className="h-4 w-4 text-red-500 mb-2" />
              <strong className="text-sm">Extract once, use many times</strong>
              <p className="text-xs text-muted-foreground mt-1">
                The cache persists across operations in the same session
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}