"use client";

import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";

export function InstallCursorButton() {
  const handleInstall = () => {
    const config = {
      "kit-dev": {
        "command": "uvx",
        "args": ["--from", "cased-kit", "kit-mcp-dev"],
        "env": {
          "OPENAI_API_KEY": "sk-...",
          "KIT_GITHUB_TOKEN": "ghp_..."
        }
      }
    };
    
    const encodedConfig = btoa(JSON.stringify(config));
    const deepLink = `cursor://anysphere.cursor-deeplink/mcp/install?name=kit-dev&config=${encodedConfig}`;
    
    window.location.href = deepLink;
  };

  return (
    <Button 
      onClick={handleInstall}
      className="neo-button bg-blue-600 hover:bg-blue-700 text-white"
      size="sm"
    >
      <Download className="h-4 w-4 mr-2" />
      Install into Cursor
    </Button>
  );
}