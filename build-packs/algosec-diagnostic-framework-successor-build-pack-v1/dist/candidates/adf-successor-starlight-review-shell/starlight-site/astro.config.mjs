import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: 'ADF Successor',
      description: 'Diagnostic playbooks and cookbooks for ASMS support work.',
      customCss: ['./src/custom.css'],
      sidebar: [
        {
          label: 'Overview',
          items: [{ label: 'Overview', slug: 'index' }],
        },
        {
          label: 'Playbooks',
          items: [
            { label: 'Playbooks', slug: 'playbooks' },
            { label: 'Service State', slug: 'playbooks/service-state' },
            { label: 'Host Health', slug: 'playbooks/host-health' },
            { label: 'Logs', slug: 'playbooks/logs' },
            { label: 'Data Collection and Processing', slug: 'playbooks/data-collection-and-processing' },
            { label: 'Distributed Node Role', slug: 'playbooks/distributed-node-role' },
          ],
        },
        {
          label: 'Cookbooks',
          items: [
            { label: 'Cookbooks', slug: 'cookbooks' },
            { label: 'Core Service Groups by Node Role', slug: 'cookbooks/core-service-groups-by-node-role' },
            { label: 'Log Entry Points', slug: 'cookbooks/log-entry-points' },
            { label: 'Data Flow Foundations', slug: 'cookbooks/data-flow-foundations' },
            { label: 'Distributed Role Foundations', slug: 'cookbooks/distributed-role-foundations' },
          ],
        },
      ],
    }),
  ],
});
