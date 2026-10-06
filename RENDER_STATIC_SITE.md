# Render Static Site deployment

This repository now has a standalone public site in `public-site/`. Keep the Flask app as the existing Free Web Service; deploy the public pages as a separate Render Static Site so the AdSense-facing pages and `robots.txt` do not sleep with the Flask service.

## Render settings

Create a new **Static Site** from this repository and use:

- Branch: `main`
- Build command: leave empty
- Publish directory: `public-site`

Choose a new service name, for example `studyhero-ai-public`. Render assigns the Static Site its own `onrender.com` URL. The landing page links to the existing Flask app at `https://studyhero-ai.onrender.com/login`.

## After deployment

1. Open the new Static Site URL and check that its home page, `/privacy.html`, `/terms.html`, `/robots.txt`, and `/ads.txt` all load.
2. In AdSense, add the new Static Site URL as a site. The existing Flask Web Service URL and the Static Site URL are different sites.
3. Keep the AdSense account meta tag and script in `public-site/index.html`; do not restore them to the Flask app's `templates/index.html`.
4. Request review for the new URL only after it is live. Google still makes the approval decision; static hosting only avoids Render Free Web Service spin-down behavior.

The publisher ID in `public-site/index.html` and `public-site/ads.txt` is the one already present in the app (`pub-6288854483652181`).
