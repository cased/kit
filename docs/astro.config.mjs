// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightLlmsTxt from 'starlight-llms-txt';

// https://astro.build/config
export default defineConfig({
  site: 'https://example.com', // Replace with your deployment URL later
  integrations: [
    starlight({
      title: 'kit 🛠️ Documentation',
      customCss: ['/src/theme.css'],
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/cased/kit' }
      ],
      sidebar: [
        {
          label: 'Introduction',
          items: [
            { label: 'Overview', slug: 'introduction/overview' },
            { label: 'Quickstart', slug: 'introduction/quickstart' },
            { label: 'Usage Guide', slug: 'introduction/usage-guide' },
          ],
        },
        {
          label: 'Core Concepts',
          items: [
            { label: 'API Primitives', slug: 'core-concepts/api-primitives' },
            { label: 'Semantic Search', slug: 'core-concepts/semantic-search' },
            { label: 'Configuring Semantic Search', slug: 'core-concepts/configuring-semantic-search' },
            { label: 'File Exclusion', slug: 'core-concepts/file-exclusion' },
            { label: 'Architecture', slug: 'core-concepts/architecture' },
            { label: 'Providing context to LLMs', slug: 'core-concepts/llm-context-best-practices' },
          ],
        },
        {
          label: 'Tutorials',
          autogenerate: { directory: 'tutorials' } 
        },
        {
          label: 'Extending Kit',
          items: [
            { label: 'Adding New Languages', slug: 'extending/adding-languages' },
          ],
        },
        {
          label: 'Development',
          items: [
            { label: 'Running Tests', slug: 'development/running-tests' },
          ]
        }
      ],
      plugins: [starlightLlmsTxt()],
    }),
  ],
});
