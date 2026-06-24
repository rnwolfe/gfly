import { defineCollection, z } from "astro:content";
import { docsLoader } from "@astrojs/starlight/loaders";
import { docsSchema } from "@astrojs/starlight/schema";

export const collections = {
  docs: defineCollection({
    loader: docsLoader(),
    // Extend Starlight's schema with freshness-triage fields (see AGENTS.md directive).
    schema: docsSchema({
      extend: z.object({
        owner: z.string().default("rnwolfe"),
        lastReviewed: z.date().optional(),
      }),
    }),
  }),
};
