import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: "ADF Prototype A \u00b7 Checkpoint Lane",
      description: "A calm triage lane for support engineers working Linux and application checks side by side.",
      customCss: ['./src/custom.css'],
      tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 2 },
      sidebar: [
        {
          label: 'Start',
          items: [{ label: 'Overview', slug: 'index' }],
        },
        {
          label: 'Sample Playbooks',
          items: [
            {
                        "label": "Application UI won't load",
                        "slug": "playbooks/application-ui-wont-load"
            },
            {
                        "label": "Application service will not start",
                        "slug": "playbooks/service-wont-start"
            },
            {
                        "label": "Linux host under pressure",
                        "slug": "playbooks/linux-host-under-pressure"
            }
],
        },
      ],
    }),
  ],
});
