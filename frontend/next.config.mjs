/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    return [
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
