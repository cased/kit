#!/bin/bash
# Launch the MCP inspector for kit-dev-mcp

echo "🚀 Launching MCP Inspector for kit-dev-mcp..."
echo ""
echo "This will start:"
echo "  1. The MCP Inspector UI"
echo "  2. The kit-dev-mcp server"
echo ""

# Launch the inspector with the kit-dev MCP server
npx @modelcontextprotocol/inspector python -m kit.mcp.dev

echo ""
echo "✨ MCP Inspector launched!"
echo "Open the URL shown above in your browser to interact with kit-dev-mcp"