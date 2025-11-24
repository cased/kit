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
          items: [
            "introduction/overview",
            "introduction/quickstart",
            "introduction/usage-guide",
            "introduction/cli",
            "changelog"
          ],
        },
        {
          label: " Repository Basics",
          items: [
            "core-concepts/repository-api",
            "core-concepts/repository-versioning",
            "core-concepts/dependency-analysis",
          ],
        },
        {
          label: " Search & Discovery",
          items: [
            "core-concepts/search-approaches",
            "core-concepts/text-search",
            "core-concepts/symbol-search",
            "core-concepts/semantic-search",
            "core-concepts/docstring-indexing",
          ],
        },
        {
          label: " AI & LLM Features",
          items: [
            "core-concepts/llm-configuration",
            "core-concepts/code-summarization",
            "core-concepts/llm-context-best-practices",
            "core-concepts/tool-calling-with-kit",
          ],
        },
        {
          label: " Advanced Features",
          items: [
            "core-concepts/incremental-analysis",
            "core-concepts/plugin-system",
          ],
        },
        {
          label: " PR Reviewer",
          items: [
            "pr-reviewer",
            "pr-reviewer/profiles",
            "pr-reviewer/integration",
            "pr-reviewer/cicd",
            "pr-reviewer/configuration",
            "pr-reviewer/examples",
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
            "tutorials/ollama",
          ],
        },
        {
          label: " API Reference",
          autogenerate: { directory: "api" },
        },
        {
          label: "🚀 kit-dev mcp",
          items: [
            "mcp/kit-dev-mcp",
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
