import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	integrations: [
		starlight({
			title: 'kit 🔧',
			social: [
				{ icon: 'github', href: 'https://github.com/tnm/kit', label: 'GitHub' },
			],
			customCss: [
				// Path to your custom CSS file, relative to the project root
				'./src/styles/terminal-theme.css',
			],
			sidebar: [
				{
					label: '📄 Introduction',
					autogenerate: { directory: 'introduction' },
				},
				{
					label: '💡 Core Concepts',
					autogenerate: { directory: 'core-concepts' },
				},
				{
					label: '📚 Tutorials',
					autogenerate: { directory: 'tutorials' },
				},
				{
					label: '⚙️ API Reference',
					autogenerate: { directory: 'api' },
				},
				{
					label: 'Development',
					autogenerate: { directory: 'development' },
				},
				{
					label: 'Extending Kit',
					autogenerate: { directory: 'extending' },
				},
			],
		}),
	],
});
