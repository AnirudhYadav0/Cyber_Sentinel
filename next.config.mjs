/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: '/:path((?!_next|api|favicon.ico).*)',
        destination: '/',
      },
    ]
  },
}

export default nextConfig
