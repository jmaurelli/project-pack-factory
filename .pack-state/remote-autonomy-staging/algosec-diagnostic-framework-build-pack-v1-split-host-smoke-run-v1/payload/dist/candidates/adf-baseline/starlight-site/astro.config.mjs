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
        label: 'Playbooks',
        items: [
          { label: "ASMS UI is down", slug: "playbooks/asms-ui-is-down" }
        ],
      },
        {
        label: 'Canonical Template',
        items: [
          { label: "Canonical Template", slug: "canonical-playbook-template" }
        ],
      }
      ],
    }),
  ],
});
