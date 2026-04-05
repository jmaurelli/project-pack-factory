import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: "ADF Prototype C \u00b7 Atlas Route",
      description: "A route-map concept that treats troubleshooting like a finite path through a Linux-backed application stack.",
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
