import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

// https://astro.build/config
export default defineConfig({
  integrations: [
    starlight({
      title: "kit ",
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
        // Remove the dedicated Recipes link, it will be picked up by Tutorials autogeneration
        // {
        // 	label: ' Recipes',
        // 	link: '/recipes', // Path to src/content/docs/recipes.mdx
        // },
        {
          label: " API Reference",
          autogenerate: { directory: "api" },
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
