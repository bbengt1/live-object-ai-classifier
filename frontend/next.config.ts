import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment (Story P10-2.2)
  // Creates a minimal production bundle that includes only necessary files
  output: 'standalone',
  images: {
    // Disable image optimization for self-hosted deployments
    // This allows images from any hostname (localhost, IP, custom domain)
    unoptimized: true,
    dangerouslyAllowSVG: true,
  },
  // Proxy API requests to backend to avoid CORS issues
  // Uses BACKEND_URL (server-side only) for internal proxying
  // NOTE: WebSocket paths (/ws, /api/v1/cameras/*/stream) are handled by
  // custom server.js upgrade handler, NOT by Next.js rewrites
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
      // NOTE: /ws is intentionally NOT included here - WebSocket upgrades
      // don't work through Next.js rewrites. They're handled in server.js
    ];
  },
};

export default nextConfig;
