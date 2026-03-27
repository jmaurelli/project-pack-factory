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
        label: 'Current Focus',
        items: [
          { label: "ASMS UI is down", slug: "playbooks/asms-ui-is-down" }
        ],
      },
        {
        label: 'Playbooks',
        items: [
          { label: "ASMS UI is down", slug: "playbooks/asms-ui-is-down" },
          { label: "FireFlow Backend", slug: "playbooks/fireflow-backend" },
          { label: "Microservice Platform", slug: "playbooks/microservice-platform" },
          { label: "Messaging and Data", slug: "playbooks/messaging-and-data" }
        ],
      }
      ],
    }),
  ],
});
