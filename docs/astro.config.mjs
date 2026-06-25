// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import starlightLlmsTxt from "starlight-llms-txt";

// https://astro.build/config
export default defineConfig({
  site: "https://docs.gfly.sh",
  integrations: [
    starlight({
      title: "gfly",
      tagline: "Google Flights for agents",
      description:
        "Docs for gfly — a read-only, JSON-first Google Flights CLI an LLM agent can drive (no API key).",
      logo: { src: "./src/assets/plane.svg", alt: "gfly" },
      customCss: ["./src/styles/gfly.css"],
      expressiveCode: { themes: ["github-dark"] },
      plugins: [
        starlightLlmsTxt({
          projectName: "gfly",
          description:
            "A read-only, JSON-first Google Flights CLI an LLM agent can drive — no API key. Stable versioned schema, semantic exit codes, token-bounded output, swappable backend.",
          exclude: ["explanation/contributing"],
        }),
      ],
      social: [
        { icon: "github", label: "GitHub", href: "https://github.com/rnwolfe/gfly" },
      ],
      editLink: { baseUrl: "https://github.com/rnwolfe/gfly/edit/main/docs/" },
      lastUpdated: true,
      head: [
        { tag: "link", attrs: { rel: "preconnect", href: "https://fonts.googleapis.com" } },
        {
          tag: "link",
          attrs: { rel: "preconnect", href: "https://fonts.gstatic.com", crossorigin: true },
        },
        {
          tag: "link",
          attrs: {
            rel: "stylesheet",
            href: "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap",
          },
        },
        { tag: "meta", attrs: { property: "og:image", content: "https://gfly.sh/og.png" } },
        { tag: "meta", attrs: { property: "og:image:width", content: "1200" } },
        { tag: "meta", attrs: { property: "og:image:height", content: "630" } },
        { tag: "meta", attrs: { name: "twitter:card", content: "summary_large_image" } },
        { tag: "meta", attrs: { name: "twitter:image", content: "https://gfly.sh/og.png" } },
      ],
      sidebar: [
        {
          label: "Start here",
          items: [
            { label: "Installation", slug: "start/installation" },
            { label: "Quickstart", slug: "start/quickstart" },
          ],
        },
        {
          label: "Guides",
          items: [
            { label: "Searching flights", slug: "guides/searching" },
            { label: "Backends", slug: "guides/backends" },
            { label: "Authentication", slug: "guides/authentication" },
            { label: "Rate limits & bans", slug: "guides/rate-limits" },
          ],
        },
        {
          label: "Reference",
          items: [{ autogenerate: { directory: "reference" } }],
        },
        {
          label: "Explanation",
          items: [
            { label: "Design & risks", slug: "explanation/design" },
            { label: "Contributing", slug: "explanation/contributing" },
          ],
        },
      ],
    }),
  ],
});
