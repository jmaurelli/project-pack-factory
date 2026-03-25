import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: "ADF Prototype B \u00b7 Signal Board",
      description: "A high-contrast operations board focused on fast scanning, hot clues, and triage pressure.",
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
