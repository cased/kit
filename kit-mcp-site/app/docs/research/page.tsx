import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen, Brain, Sparkles, AlertCircle, CheckCircle } from "lucide-react";

export default function ResearchPage() {
  return (
    <div className="prose prose-slate max-w-none">
      <div className="not-prose mb-8">
        <Badge variant="secondary" className="neo-badge bg-yellow-300 text-black mb-4">
          Core Feature
        </Badge>
        <h1 className="text-4xl font-bold mb-4">Deep Package Research</h1>
        <p className="text-xl text-muted-foreground">
          AI-powered comprehensive package documentation using LLM knowledge
        </p>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">How It Works</h2>
        <p className="text-muted-foreground mb-6">
          The deep research feature leverages LLM knowledge to provide comprehensive documentation
          about any package, library, or framework. It uses a single, powerful prompt to extract
          detailed information from the model's training data.
        </p>
        
        <Card className="neo-card border-2 border-purple-500">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-purple-500" />
                Multi-Source Documentation Research
              </CardTitle>
              <div className="flex gap-2">
                <Badge className="neo-badge bg-purple-100 text-purple-800">
                  Context7
                </Badge>
                <Badge className="neo-badge bg-blue-100 text-blue-800">
                  Chroma Package Search
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Combines multiple documentation sources for comprehensive package research. Uses Chroma Package Search
              for source code exploration and Context7 for documentation aggregation. When you provide a
              specific query, results are enhanced with LLM synthesis for comprehensive answers.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="font-semibold mb-2">Documentation Sources:</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• <strong>Chroma Package Search:</strong> Source code exploration</li>
                  <li>• <strong>Context7:</strong> Real-time docs aggregation</li>
                  <li>• Official package documentation</li>
                  <li>• Latest API references</li>
                  <li>• Real code examples from repositories</li>
                  <li>• LLM synthesis (when query provided)</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-2">How It Works:</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Searches package source code via Chroma</li>
                  <li>• Fetches documentation from Context7</li>
                  <li>• Combines both sources intelligently</li>
                  <li>• Returns code examples & docs</li>
                  <li>• Optionally enhances with LLM</li>
                </ul>
                <div className="mt-3 p-2 bg-blue-50 rounded">
                  <p className="text-xs text-blue-700">
                    <strong>✨ Key Benefit:</strong> Both source code and docs in one query
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Usage Examples</h2>
        
        <div className="space-y-6">
          {/* Basic Example */}
          <div>
            <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Basic Package Research
            </h3>
            <Card className="not-prose">
              <CardContent className="p-4">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white">
{`# Research a package
deep_research_package({
  "package_name": "fastapi"
})

# Returns real-time documentation + synthesis:
{
  "package": "fastapi",
  "status": "success",
  "documentation": {
    "snippets": [
      {
        "title": "FastAPI Quickstart",
        "description": "Basic FastAPI application setup",
        "code": "from fastapi import FastAPI..."
      }
    ],
    "total_snippets": 47
  },
  "chroma_results": [
    {
      "file_path": "fastapi/applications.py",
      "line_number": 45,
      "content": "class FastAPI(Starlette):"
    }
  ],
  "source": "multi_source",
  "providers": ["ChromaPackageSearch", "UpstashProvider"],
  "version": "2.0.0"
}`}</pre>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Specific Topic Example */}
          <div>
            <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-blue-500" />
              Research Specific Topics
            </h3>
            <Card className="not-prose">
              <CardContent className="p-4">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white">
{`# Research specific aspect of a package
deep_research_package({
  "package_name": "fastapi",
  "query": "how to implement OAuth2 authentication"
})

# Returns real docs + LLM synthesis:
{
  "package": "fastapi",
  "query": "how to implement OAuth2 authentication",
  "status": "success",
  "documentation": {
    "snippets": [...] // Real FastAPI OAuth2 code examples
  },
  "chroma_results": [
    {
      "file_path": "fastapi/security/oauth2.py",
      "snippet": "OAuth2 implementation details..."
    }
  ],
  "answer": "To implement OAuth2 in FastAPI, you can use the built-in security utilities...",
  "source": "multi_source+llm",
  "providers": ["ChromaPackageSearch", "UpstashProvider"]
}`}</pre>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Framework Comparison */}
          <div>
            <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-purple-500" />
              Compare Packages
            </h3>
            <Card className="not-prose">
              <CardContent className="p-4">
                <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
                  <pre className="text-white">
{`# Compare similar packages
deep_research_package({
  "package_name": "fastapi vs flask vs django"
})

# Returns comparative analysis:
{
  "comparison": "FastAPI vs Flask vs Django",
  "summary_table": {
    "performance": {...},
    "features": {...},
    "learning_curve": {...},
    "use_cases": {...}
  },
  "detailed_comparison": [...],
  "migration_guides": [...],
  "recommendation": "Choose based on..."
}`}</pre>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Configuration</h2>
        <Card className="not-prose">
          <CardContent className="p-4">
            <div className="border-2 border-black bg-black rounded-lg p-4 font-mono text-sm">
              <pre className="text-white">
{`# Set up your providers (optional but recommended)

# For source code search (Chroma Package Search)
export CHROMA_PACKAGE_SEARCH_API_KEY="your-chroma-key"
# Get from: https://cloud.trychroma.com

# For LLM synthesis (choose one)
# Option 1: OpenAI
export OPENAI_API_KEY="your-openai-key"

# Option 2: Anthropic
export ANTHROPIC_API_KEY="your-anthropic-key"

# Option 3: Ollama (free, local)
# Install: curl -fsSL https://ollama.com/install.sh | sh
# Pull model: ollama pull qwen2.5-coder:latest
# No API key needed!

# The tool will use all available providers automatically
deep_research_package({
  "package_name": "numpy",
  "query": "FFT implementation"  # Optional
})`}</pre>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="my-8">
        <h2 className="text-2xl font-bold mb-4">Key Benefits</h2>
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
            <div>
              <h3 className="font-semibold">Always Up-to-Date</h3>
              <p className="text-sm text-muted-foreground">
                LLMs are trained on recent data, providing current documentation even for new packages.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <CheckCircle className="h-5 w-5 text-blue-500 mt-0.5" />
            <div>
              <h3 className="font-semibold">Comprehensive Coverage</h3>
              <p className="text-sm text-muted-foreground">
                Get documentation for any package, even obscure ones, thanks to broad LLM training.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <CheckCircle className="h-5 w-5 text-purple-500 mt-0.5" />
            <div>
              <h3 className="font-semibold">Contextual Understanding</h3>
              <p className="text-sm text-muted-foreground">
                Ask about specific use cases, integrations, or comparisons - the LLM understands context.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="my-8">
        <Card className="neo-card border-2 border-amber-500 bg-amber-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-amber-600" />
              Important Notes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="text-sm space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-amber-600">•</span>
                <span>
                  <strong>API Key Required:</strong> You need an LLM API key (OpenAI, Anthropic, etc.) 
                  or use Ollama locally for free.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600">•</span>
                <span>
                  <strong>Cost Considerations:</strong> Each research query uses LLM tokens. 
                  Monitor usage to control costs, or use Ollama for free local inference.
                </span>
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      <div className="my-8 p-6 bg-gradient-to-r from-green-50 to-blue-50 rounded-lg border-2 border-green-200">
        <h3 className="text-lg font-bold mb-2">
          🚀 Quick Start with Ollama (Free)
        </h3>
        <p className="text-sm text-muted-foreground mb-3">
          Get started with deep research using free, local AI:
        </p>
        <div className="bg-white p-3 rounded border border-green-200">
          <pre className="text-xs">
{`# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a coding model
ollama pull qwen2.5-coder:latest

# 3. Use with kit-dev-mcp (no API key needed!)
deep_research_package({
  "package_name": "requests"
})`}</pre>
        </div>
      </div>
    </div>
  );
}