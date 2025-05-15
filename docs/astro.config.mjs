import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import starlightLLMsTXT from "starlight-llms-txt";

// https://astro.build/config
export default defineConfig({
  site: "https://kit.cased.com",
  integrations: [
    starlight({
      title: "kit ",
      plugins: [starlightLLMsTXT()],
      social: [
        {
          icon: "github",
          href: "https://github.com/cased/kit",
          label: "GitHub",
        },
      ],
      customCss: [
        // Path to your custom CSS file, relative to the project root
        "./src/styles/theme.css",
      ],
      markdown: { headingLinks: false },
      sidebar: [
        {
          label: " Introduction",
          autogenerate: { directory: "introduction" },
        },
        {
          label: " Core Concepts",
          items: [
            // Manually specify order, starting with repository-api
            "core-concepts/repository-api",
            "core-concepts/search-approaches",
            "core-concepts/code-summarization",
            "core-concepts/docstring-indexing",
            "core-concepts/tool-calling-with-kit",
            "core-concepts/semantic-search",
            "core-concepts/configuring-semantic-search",
            "core-concepts/dependency-analysis",
            "core-concepts/llm-context-best-practices",
            "core-concepts/context-assembly",
          ],
        },
        {
          label: " Tutorials",
          items: [
            "tutorials/ai_pr_reviewer",
            "tutorials/codebase-qa-bot",
            "tutorials/codebase_summarizer",
            "tutorials/dependency_graph_visualizer",
            "tutorials/docstring_search",
            "tutorials/dump_repo_map",
            "tutorials/integrating_supersonic",
            "tutorials/recipes",
          ],
        },
        {
          label: " API Reference",
          autogenerate: { directory: "api" },
        },
        {
          label: " MCP",
          items: [
            "mcp/using-kit-with-mcp",
          ],
        },
        {
          label: " Development",
          autogenerate: { directory: "development" },
        },
        {
          label: " Extending Kit",
          autogenerate: { directory: "extending" },
        },
      ],
    }),
  ],
});
