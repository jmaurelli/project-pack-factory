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
          { label: "ASMS UI is down", slug: "playbooks/asms-ui-is-down" },
          { label: "ASMS Keycloak auth is down", slug: "playbooks/asms-keycloak-auth-is-down" }
        ],
      },
        {
        label: 'Guides',
        items: [
          { label: "ASMS / Keycloak integration guide", slug: "guides/asms-keycloak-integration-guide" },
          { label: "ASMS / Keycloak junior operator guide", slug: "guides/asms-keycloak-junior-operator-guide" }
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
