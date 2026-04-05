import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: "ADF Prototype 3 \u00b7 Support Cockpit",
      description: "A compact support cockpit for fast scanning under pressure, with commands and healthy output kept close together.",
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
