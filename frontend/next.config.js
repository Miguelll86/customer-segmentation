/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // In sviluppo le chiamate /api vanno al backend locale; in produzione usa NEXT_PUBLIC_API_URL
  async rewrites() {
    if (process.env.NEXT_PUBLIC_API_URL) return [];
    return [{ source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' }];
  },
};

module.exports = nextConfig;
