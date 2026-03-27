import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: 'AlgoSec Diagnostic Framework',
      description: 'Target-backed diagnostic playbooks for support engineers.',
      disable404Route: true,
      customCss: ['./src/custom.css'],
      tableOfContents: false,
      sidebar: [
        {
          label: 'Start Here',
          items: [{ label: 'Overview', slug: 'index' }],
        },
        {
        label: 'Canonical Template',
        items: [
          { label: "Field Manual", slug: "canonical-playbook-template" }
        ],
      }
      ],
    }),
  ],
});
