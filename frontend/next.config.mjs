/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    return [
      {
        source: "/",
        destination: "/food",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
