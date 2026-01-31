# sun2flops

A minimal static landing page for the Sun2Flops Vercel deployment.

## Deploying to Vercel

This repo uses a static `index.html` with a `vercel.json` that configures the
`@vercel/static` builder. Deploying the main branch should now return the landing
page instead of a 404.

If you want to move to a framework later (Next.js, Astro, etc.), replace the
static files with your app and update the Vercel configuration accordingly.
