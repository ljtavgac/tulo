/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    // Computed redirects for a page that's been unpublished as a
    // duplicate of another, still-published one (see backend/app/main.py's
    // GET /redirects and seed_templates.py's redirect_to convention) --
    // fetched at build time rather than hand-maintained here, since a
    // duplicate can get unpublished at any point and a next.config.mjs
    // edit for each one would be easy to forget (a real, confirmed gap:
    // quick-pickled-beets was unpublished with no redirect at all, so an
    // old link or bookmark to it just 404'd instead of landing on
    // pickled-beets). Fails open to no dynamic redirects (not a failed
    // build) if the backend is unreachable at build time -- local dev
    // without a backend running, most of all.
    let dynamicRedirects = [];
    try {
      const apiUrl = process.env.API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/redirects`);
      if (res.ok) {
        const pairs = await res.json();
        dynamicRedirects = pairs.map(({ source, destination }) => ({
          source,
          destination,
          permanent: true,
        }));
      }
    } catch {
      // Backend unreachable at build time -- proceed with just the static
      // redirects below rather than failing the whole build over this.
    }

    return [
      ...dynamicRedirects,
      // /food used to be the homepage (redirected here). Now the reverse:
      // / is the real homepage and /food is what redirects, now that a
      // separate /food landing page is just duplicate content with only
      // one vertical live. permanent: true emits a 308 (not a literal
      // 301) -- Next.js's own deliberate choice over 301/302, since 308
      // (like 307) preserves the original request method across the
      // redirect; treated identically to 301 by search engines for
      // ranking/consolidation purposes, and consistent with how this
      // site's other permanent redirect (the www subdomain, in Vercel's
      // domain settings) is already handled.
      {
        source: "/food",
        destination: "/",
        permanent: true,
      },
      // /food/vs -> /food/comparisons: the comparison template's URL
      // segment was renamed for clearer wording. Kept as a real redirect
      // rather than just letting the old path 404 -- these pages have
      // been live and in the sitemap, so any existing bookmark, external
      // link, or search-engine-cached URL should still resolve rather
      // than dead-end, and a redirect costs nothing to keep around.
      {
        source: "/food/vs",
        destination: "/food/comparisons",
        permanent: true,
      },
      {
        source: "/food/vs/:slug",
        destination: "/food/comparisons/:slug",
        permanent: true,
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "images.pexels.com",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
