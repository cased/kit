import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Code2, Sparkles, GitBranch, BookOpen } from "lucide-react";

export default function ExamplesPage() {
  return (
    <div className="prose prose-slate max-w-none">
      <div className="not-prose mb-8">
        <Badge variant="secondary" className="neo-badge bg-yellow-300 text-black mb-4">
          Examples
        </Badge>
        <h1 className="text-4xl font-bold mb-4">Real-World Examples</h1>
        <p className="text-xl text-muted-foreground">
          Common development scenarios using kit-mcp-dev
        </p>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Understanding a New Codebase</h2>
        <Card className="neo-card not-prose">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Scenario: Onboarding to a new project
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              You've just joined a team and need to understand their React + FastAPI application.
            </p>
            <Tabs defaultValue="conversation" className="w-full">
              <TabsList>
                <TabsTrigger value="conversation">Conversation</TabsTrigger>
                <TabsTrigger value="tools">Tools Used</TabsTrigger>
              </TabsList>
              
              <TabsContent value="conversation">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-xs space-y-4">
                  <div>
                    <span className="text-blue-400">You:</span>
                    <p className="text-gray-300 ml-4">Using Kit, help me understand this codebase at /Users/me/new-project</p>
                  </div>
                  
                  <div>
                    <span className="text-white">AI:</span>
                    <div className="text-gray-300 ml-4 space-y-2">
                      <p>I'll analyze the codebase structure and key components for you.</p>
                      <p className="text-xs text-gray-500">[Opening repository...]</p>
                      <p className="text-xs text-gray-500">[Extracting symbols and analyzing structure...]</p>
                      <p className="text-xs text-gray-500">[Building smart context...]</p>
                      <p>Here's what I found:</p>
                      <ul className="list-disc ml-4 mt-2">
                        <li>Full-stack application with React frontend and FastAPI backend</li>
                        <li>Authentication using JWT tokens (see backend/auth/jwt_handler.py)</li>
                        <li>PostgreSQL database with SQLAlchemy ORM</li>
                        <li>Redux for state management in frontend</li>
                        <li>Docker compose setup for local development</li>
                      </ul>
                      <p className="mt-2">Key entry points:</p>
                      <ul className="list-disc ml-4">
                        <li>Backend: backend/main.py - FastAPI application initialization</li>
                        <li>Frontend: frontend/src/App.tsx - Main React component</li>
                        <li>Database models: backend/models/ directory</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="tools">
                <div className="space-y-3">
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">open_repository(path="/Users/me/new-project")</code>
                  </div>
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">get_file_tree(repo_id="...")</code>
                  </div>
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">extract_symbols(repo_id="...", file_path="backend/main.py")</code>
                  </div>
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">build_smart_context(repo_id="...", task="understand application architecture")</code>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Implementing a New Feature</h2>
        <Card className="neo-card not-prose">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code2 className="h-5 w-5 text-primary" />
              Scenario: Adding OAuth2 authentication
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              You need to add Google OAuth2 login to an existing application.
            </p>
            <Tabs defaultValue="conversation" className="w-full">
              <TabsList>
                <TabsTrigger value="conversation">Conversation</TabsTrigger>
                <TabsTrigger value="tools">Tools Used</TabsTrigger>
              </TabsList>
              
              <TabsContent value="conversation">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-xs space-y-4">
                  <div>
                    <span className="text-blue-400">You:</span>
                    <p className="text-gray-300 ml-4">Using Kit, help me implement Google OAuth2 authentication</p>
                  </div>
                  
                  <div>
                    <span className="text-white">AI:</span>
                    <div className="text-gray-300 ml-4 space-y-2">
                      <p>I'll help you implement Google OAuth2. Let me research the best approach and check your current auth setup.</p>
                      <p className="text-xs text-gray-500">[Researching OAuth2 documentation...]</p>
                      <p className="text-xs text-gray-500">[Analyzing existing authentication code...]</p>
                      <p className="text-xs text-gray-500">[Building implementation context...]</p>
                      <p>Based on my analysis:</p>
                      <ol className="list-decimal ml-4 mt-2">
                        <li>You already have JWT authentication in place (auth/jwt_handler.py)</li>
                        <li>I found the authlib package would work well with your FastAPI backend</li>
                        <li>Here's the implementation plan:</li>
                      </ol>
                      <div className="bg-slate-800 rounded p-2 mt-2">
                        <p className="text-xs">1. Install dependencies: pip install authlib httpx</p>
                        <p className="text-xs">2. Create backend/auth/oauth2.py for Google OAuth flow</p>
                        <p className="text-xs">3. Add OAuth endpoints to your FastAPI router</p>
                        <p className="text-xs">4. Update frontend with Google login button</p>
                      </div>
                      <p className="mt-2">I've found similar patterns in your codebase that we can follow...</p>
                    </div>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="tools">
                <div className="space-y-3">
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">deep_research_package(package_name="authlib", use_context7=true)</code>
                  </div>
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">find_symbol_usages(repo_id="...", symbol_name="authenticate")</code>
                  </div>
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">build_smart_context(repo_id="...", task="implement OAuth2 authentication")</code>
                  </div>
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">search_code(repo_id="...", query="login")</code>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Debugging with Documentation</h2>
        <Card className="neo-card not-prose">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-primary" />
              Scenario: Debugging a React hooks issue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Your useEffect hook is causing infinite re-renders.
            </p>
            <Tabs defaultValue="conversation" className="w-full">
              <TabsList>
                <TabsTrigger value="conversation">Conversation</TabsTrigger>
                <TabsTrigger value="tools">Tools Used</TabsTrigger>
              </TabsList>
              
              <TabsContent value="conversation">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-xs space-y-4">
                  <div>
                    <span className="text-blue-400">You:</span>
                    <p className="text-gray-300 ml-4">Using Kit, help me fix this infinite re-render in components/Dashboard.tsx</p>
                  </div>
                  
                  <div>
                    <span className="text-white">AI:</span>
                    <div className="text-gray-300 ml-4 space-y-2">
                      <p>Let me analyze the component and research React hooks best practices.</p>
                      <p className="text-xs text-gray-500">[Reading Dashboard.tsx...]</p>
                      <p className="text-xs text-gray-500">[Researching React useEffect documentation...]</p>
                      <p className="text-xs text-gray-500">[Analyzing dependencies...]</p>
                      <p>I found the issue! In Dashboard.tsx line 45:</p>
                      <div className="bg-slate-800 rounded p-2 mt-2">
                        <p className="text-white">// Problem:</p>
                        <p className="text-xs">{`useEffect(() => {`}</p>
                        <p className="text-xs">{`  setData({...data, newField});`}</p>
                        <p className="text-xs">{`}, [data]); // data is recreated each render!`}</p>
                      </div>
                      <p className="mt-2">The fix (based on React docs):</p>
                      <div className="bg-slate-800 rounded p-2 mt-2">
                        <p className="text-white">// Solution:</p>
                        <p className="text-xs">{`useEffect(() => {`}</p>
                        <p className="text-xs">{`  setData(prev => ({...prev, newField}));`}</p>
                        <p className="text-xs">{`}, []); // Use functional update instead`}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="tools">
                <div className="space-y-3">
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">get_file_content(repo_id="...", file_path="components/Dashboard.tsx")</code>
                  </div>
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">deep_research_package(package_name="react", use_context7=true)</code>
                  </div>
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">extract_symbols(repo_id="...", file_path="components/Dashboard.tsx")</code>
                  </div>
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">semantic_search(repo_id="...", query="useEffect hooks dependencies")</code>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Code Review Preparation</h2>
        <Card className="neo-card not-prose">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitBranch className="h-5 w-5 text-primary" />
              Scenario: Reviewing a pull request
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              You need to review a colleague's pull request for a new feature.
            </p>
            <Tabs defaultValue="conversation" className="w-full">
              <TabsList>
                <TabsTrigger value="conversation">Conversation</TabsTrigger>
                <TabsTrigger value="tools">Tools Used</TabsTrigger>
              </TabsList>
              
              <TabsContent value="conversation">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-xs space-y-4">
                  <div>
                    <span className="text-blue-400">You:</span>
                    <p className="text-gray-300 ml-4">Using Kit, help me review the changes in the feature/user-profile branch</p>
                  </div>
                  
                  <div>
                    <span className="text-white">AI:</span>
                    <div className="text-gray-300 ml-4 space-y-2">
                      <p>I'll analyze the changes and provide a comprehensive review.</p>
                      <p className="text-xs text-gray-500">[Reviewing diff between main and feature/user-profile...]</p>
                      <p className="text-xs text-gray-500">[Running tests on the feature branch...]</p>
                      <p className="text-xs text-gray-500">[Checking for similar patterns...]</p>
                      <p>Review Summary:</p>
                      <ul className="list-disc ml-4 mt-2">
                        <li className="text-red-300">✓ Code follows existing patterns</li>
                        <li className="text-yellow-300">⚠ Found potential issue in user_profile.py line 67</li>
                        <li className="text-blue-300">ℹ Similar implementation exists in admin_profile.py</li>
                      </ul>
                      <p className="mt-2">Specific feedback:</p>
                      <ol className="list-decimal ml-4">
                        <li>Missing input validation for email field</li>
                        <li>Consider reusing the ProfileValidator from utils/validators.py</li>
                        <li>The database migration looks good</li>
                      </ol>
                    </div>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="tools">
                <div className="space-y-3">
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">review_diff(repo_id="...", base="main", head="feature/user-profile")</code>
                  </div>
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">get_git_info(repo_id="...")</code>
                  </div>
                  <div className="bg-slate-100 rounded-lg p-3">
                    <code className="text-sm">search_code(repo_id="...", query="UserProfile")</code>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Tips for Effective Use</h2>
        <div className="not-prose grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="text-lg">Start with Context</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Always begin by opening the repository and building context for your task. 
                This helps the AI understand your codebase structure.
              </p>
            </CardContent>
          </Card>
          
          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="text-lg">Use Natural Language</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Start requests with "Using Kit, ..." to ensure the AI uses the MCP tools 
                rather than trying to guess or hallucinate.
              </p>
            </CardContent>
          </Card>
          
          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="text-lg">Leverage Documentation</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Use deep_research_package when working with unfamiliar libraries. 
                The context7.com integration provides excellent examples.
              </p>
            </CardContent>
          </Card>
          
          <Card className="neo-card">
            <CardHeader>
              <CardTitle className="text-lg">Test as You Go</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Use semantic_search to find related code by meaning, not just keywords. 
                This helps identify patterns and similar implementations.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}