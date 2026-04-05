import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: "ADF Prototype 2 \u00b7 Mission Board",
      description: "A visual mission board that turns deterministic troubleshooting into a sequence of bold checkpoints and stop points.",
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
