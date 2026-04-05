import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: 'AlgoSec Diagnostic Framework',
      description: 'Diagnostic playbooks and cookbooks for ASMS support work.',
      disable404Route: true,
      tableOfContents: false,
      customCss: ['./src/custom.css'],
      sidebar: [
        {
                "label": "Overview",
                "items": [
                        {
                                "label": "AlgoSec Diagnostic Framework",
                                "slug": "index"
                        }
                ]
        },
        {
                "label": "Playbooks",
                "items": [
                        {
                                "label": "Index",
                                "slug": "playbooks"
                        },
                        {
                                "label": "Service State",
                                "slug": "playbooks/service-state"
                        },
                        {
                                "label": "Logs",
                                "slug": "playbooks/logs"
                        }
                ]
        },
        {
                "label": "Cookbooks",
                "items": [
                        {
                                "label": "Index",
                                "slug": "cookbooks"
                        },
                        {
                                "label": "Core Service Groups by Node Role",
                                "slug": "cookbooks/core-service-groups-by-node-role"
                        }
                ]
        }
],
    }),
  ],
});
