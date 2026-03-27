import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: 'AlgoSec Diagnostic Framework',
      description: 'Target-backed diagnostic playbooks for support engineers.',
      customCss: ['./src/custom.css'],
      tableOfContents: false,
      sidebar: [
        {
          label: 'Start Here',
          items: [{ label: 'Overview', slug: 'index' }],
        },
        {
        label: 'Current Focus',
        items: [],
      },
        {
        label: 'Playbooks',
        items: [],
      }
      ],
    }),
  ],
});
