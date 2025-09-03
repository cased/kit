#!/bin/bash
# Kit MCP Optimizer - Configure your AI to use Kit tools effectively
# Usage: curl -sSL https://your-site.com/kit-optimize.sh | bash

set -e

echo "🚀 Kit MCP Optimizer v1.0"
echo "========================="
echo ""

# Create .kit-prompts.md for project-specific prompts
cat > .kit-prompts.md << 'EOF'
# Kit MCP Integration for This Project

## MANDATORY: Use these tools for ALL code tasks

### 1. Repository Analysis
- `open_repository` - Load the codebase first
- `get_file_tree` - Understand project structure
- `extract_symbols` - Fast cached symbol extraction

### 2. Code Search & Navigation
- `search_text` - Powerful regex search
- `find_symbol_usages` - Track where symbols are used
- `get_dependency_graph` - Map import relationships

### 3. Documentation Research
- `deep_research_package` - Multi-source documentation
- `context7_research` - AI-aggregated docs from context7.com
- `build_smart_context` - Task-aware context building

## Workflow for EVERY code task:
1. Open repository with `open_repository`
2. Get structure with `get_file_tree`
3. Extract symbols with `extract_symbols` (cached!)
4. Research packages with `deep_research_package`
5. Build context with `build_smart_context`
6. THEN provide solution

## Why this matters:
- Better context = More accurate suggestions
- Cached operations = Faster responses
- Multi-source docs = Complete understanding
- Smart context = Fewer mistakes

Remember: ALWAYS gather context before suggesting code changes.
EOF

# Create .cursorrules if using Cursor
if [ -d ".cursor" ] || command -v cursor &> /dev/null; then
    cat > .cursorrules << 'EOF'
# Cursor Rules - Kit MCP Integration

You have access to kit-mcp-dev. ALWAYS use these tools:

## Required for EVERY task:
1. open_repository - Load codebase
2. get_file_tree - Navigate structure
3. extract_symbols - Analyze code (cached!)

## For implementation:
- deep_research_package - Research before using libraries
- context7_research - Get AI-aggregated docs
- build_smart_context - Gather task context

## For debugging:
- search_text - Find implementations
- find_symbol_usages - Track usage
- get_dependency_graph - Understand relationships

Never suggest code without using these tools first.
EOF
    echo "✅ Created .cursorrules for Cursor IDE"
fi

# Create Claude project instructions
if [ ! -f ".claude-instructions.md" ]; then
    cat > .claude-instructions.md << 'EOF'
# Claude Project Instructions

When using Kit MCP tools:

1. **Always start with context**
   - open_repository
   - get_file_tree
   - extract_symbols

2. **Research before implementing**
   - deep_research_package for libraries
   - context7_research for AI docs
   - build_smart_context for tasks

3. **Use cached operations**
   - extract_symbols is FAST
   - Don't hesitate to use it frequently

Better context = Better code. Always.
EOF
    echo "✅ Created .claude-instructions.md"
fi

echo ""
echo "✨ Kit MCP Optimizer Complete!"
echo ""
echo "📝 Files created:"
echo "   - .kit-prompts.md (main prompt file)"
[ -f ".cursorrules" ] && echo "   - .cursorrules (Cursor IDE integration)"
[ -f ".claude-instructions.md" ] && echo "   - .claude-instructions.md (Claude instructions)"
echo ""
echo "🎯 Next steps:"
echo "1. Include .kit-prompts.md in your AI conversations"
echo "2. Commit these files to your repository"
echo "3. Your AI will now automatically use Kit tools!"
echo ""
echo "💡 Pro tip: Tell your AI to 'read .kit-prompts.md' at the start of each session"