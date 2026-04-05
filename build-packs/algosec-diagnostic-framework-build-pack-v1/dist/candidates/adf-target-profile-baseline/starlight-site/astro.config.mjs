import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: 'AlgoSec Diagnostic Framework',
      description: 'Target-backed diagnostic playbooks for support engineers.',
      disable404Route: true,
      customCss: ['./src/custom.css'],
      head: [
        {
          tag: 'script',
          attrs: { type: 'module', src: '/adf-field-manual.js' },
        },
      ],
      tableOfContents: false,
      sidebar: [
        {
          label: 'Start Here',
          items: [{ label: 'Overview', slug: 'index' }],
        },
        {
        label: 'Playbooks',
        items: [
          { label: "ASMS UI is down", slug: "playbooks/asms-ui-is-down" },
          { label: "FireFlow Backend", slug: "playbooks/fireflow-backend" },
          { label: "Microservice Platform", slug: "playbooks/microservice-platform" },
          { label: "Messaging and Data", slug: "playbooks/messaging-and-data" },
          { label: "ASMS Keycloak auth is down", slug: "playbooks/asms-keycloak-auth-is-down" }
        ],
      },
        {
        label: 'Guides',
        items: [
          { label: "ASMS Runtime Taxonomy Guide", slug: "guides/asms-runtime-taxonomy-guide" },
          { label: "ASMS / Keycloak integration guide", slug: "guides/asms-keycloak-integration-guide" },
          { label: "ASMS / Keycloak Tier 2 support guide", slug: "guides/asms-keycloak-tier-2-support-guide" }
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
