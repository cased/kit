import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileCode2, GitBranch, Folder, Globe } from "lucide-react";

export default function RepositoryPage() {
  return (
    <div className="prose prose-slate max-w-none">
      <div className="not-prose mb-8">
        <Badge variant="secondary" className="neo-badge bg-yellow-300 text-black mb-4">
          Core Feature
        </Badge>
        <h1 className="text-4xl font-bold mb-4">Repository Management</h1>
        <p className="text-xl text-muted-foreground">
          Open and analyze local or remote repositories with Kit's powerful tools
        </p>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Overview</h2>
        <p className="text-muted-foreground mb-6">
          Repository management is the foundation of Kit MCP. Once you open a repository, 
          you get access to all of Kit's code intelligence features: symbol extraction, 
          dependency analysis, code search, and more.
        </p>
      </div>

      <Card className="neo-card my-8">
        <CardHeader>
          <CardTitle>Available Tools</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h4 className="font-mono-accent text-red-600 font-semibold">open_repository</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Opens a local directory or GitHub repository for analysis
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm mt-2">
                <code className="text-white text-xs">
                  open_repository(path="/path/to/repo")
                </code>
              </div>
            </div>
            
            <div>
              <h4 className="font-mono-accent text-red-600 font-semibold">get_file_tree</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Returns the complete file structure of the repository
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm mt-2">
                <code className="text-white text-xs">
                  get_file_tree(repo_id="...", path="/src")
                </code>
              </div>
            </div>
            
            <div>
              <h4 className="font-mono-accent text-red-600 font-semibold">get_file_content</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Read one or multiple files from the repository
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm mt-2">
                <code className="text-white text-xs">
                  get_file_content(repo_id="...", file_path="main.py")
                </code>
              </div>
            </div>
            
            <div>
              <h4 className="font-mono-accent text-red-600 font-semibold">get_file_content_multi</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Read multiple files in a single efficient operation
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm mt-2">
                <code className="text-white text-xs">
                  get_file_content_multi(repo_id="...", file_paths=["main.py", "utils.py"])
                </code>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Opening Repositories</h2>
        <Tabs defaultValue="local" className="w-full">
          <TabsList>
            <TabsTrigger value="local">Local Repository</TabsTrigger>
            <TabsTrigger value="github">GitHub Repository</TabsTrigger>
            <TabsTrigger value="private">Private Repository</TabsTrigger>
          </TabsList>
          
          <TabsContent value="local">
            <Card className="neo-card">
              <CardContent className="p-6">
                <p className="text-sm text-muted-foreground mb-4">
                  Open a local repository by providing the absolute path:
                </p>
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white text-sm">
                    <code>{`# Ask your AI:
"Open the repository at /Users/me/my-project"

# Or be specific:
"Using Kit, open the project at /Users/me/my-project"

# The AI will execute:
open_repository(path="/Users/me/my-project")`}</code>
                  </pre>
                </div>
                <p className="text-sm text-muted-foreground mt-4">
                  <strong>Tip:</strong> The repository ID returned is used for all subsequent operations.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="github">
            <Card className="neo-card">
              <CardContent className="p-6">
                <p className="text-sm text-muted-foreground mb-4">
                  Open public GitHub repositories by URL:
                </p>
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white text-sm">
                    <code>{`# Ask your AI:
"Open the repository https://github.com/cased/kit"

# The AI will execute:
open_repository(path="https://github.com/cased/kit")`}</code>
                  </pre>
                </div>
                <p className="text-sm text-muted-foreground mt-4">
                  Kit will clone the repository to a temporary directory for analysis.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="private">
            <Card className="neo-card">
              <CardContent className="p-6">
                <p className="text-sm text-muted-foreground mb-4">
                  For private repositories, set your GitHub token:
                </p>
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white text-sm">
                    <code>{`# Set in your MCP configuration:
"env": {
  "KIT_GITHUB_TOKEN": "ghp_your_token_here"
}

# Then open normally:
open_repository(path="https://github.com/org/private-repo")`}</code>
                  </pre>
                </div>
                <p className="text-sm text-muted-foreground mt-4">
                  Your token needs <code className="command-highlight">repo</code> scope for private access.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Working with Files</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <Folder className="h-4 w-4 mr-2 text-red-500" />
                File Navigation
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">
                Explore repository structure:
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                <code className="text-white text-xs">
                  get_file_tree(repo_id="...")
                </code>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Returns structured file tree with paths and metadata
              </p>
            </CardContent>
          </Card>
          
          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <FileCode2 className="h-4 w-4 mr-2 text-red-500" />
                Batch Reading
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">
                Read multiple files efficiently:
              </p>
              <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                <code className="text-white text-xs">
                  get_file_content_multi(...)
                </code>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Single operation for multiple files - much faster!
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Repository Metadata</h2>
        <Card className="neo-card">
          <CardContent className="p-6">
            <p className="text-muted-foreground mb-4">
              When you open a repository, Kit provides access to Git metadata:
            </p>
            <div className="space-y-3">
              <div className="flex items-start">
                <GitBranch className="h-4 w-4 text-red-500 mr-2 mt-1" />
                <div>
                  <strong className="text-sm">Current Branch</strong>
                  <p className="text-xs text-muted-foreground">Access via repository.current_branch</p>
                </div>
              </div>
              <div className="flex items-start">
                <GitBranch className="h-4 w-4 text-red-500 mr-2 mt-1" />
                <div>
                  <strong className="text-sm">Current SHA</strong>
                  <p className="text-xs text-muted-foreground">Access via repository.current_sha</p>
                </div>
              </div>
              <div className="flex items-start">
                <Globe className="h-4 w-4 text-red-500 mr-2 mt-1" />
                <div>
                  <strong className="text-sm">Remote URL</strong>
                  <p className="text-xs text-muted-foreground">Access via repository.remote_url</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Best Practices</h2>
        <div className="space-y-3">
          <Card className="neo-card">
            <CardContent className="p-4">
              <strong className="text-sm">1. Always open repository first</strong>
              <p className="text-xs text-muted-foreground mt-1">
                All other operations require an open repository with a valid repo_id
              </p>
            </CardContent>
          </Card>
          <Card className="neo-card">
            <CardContent className="p-4">
              <strong className="text-sm">2. Use file trees for navigation</strong>
              <p className="text-xs text-muted-foreground mt-1">
                get_file_tree helps understand structure before reading files
              </p>
            </CardContent>
          </Card>
          <Card className="neo-card">
            <CardContent className="p-4">
              <strong className="text-sm">3. Batch file reads when possible</strong>
              <p className="text-xs text-muted-foreground mt-1">
                get_file_content_multi is more efficient than multiple single reads
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}