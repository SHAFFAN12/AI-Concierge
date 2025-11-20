import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: `
              default-src 'self';
              script-src 'self' 'unsafe-inline' ${process.env.NODE_ENV === 'development' ? "'unsafe-eval'" : ''};
              style-src 'self' 'unsafe-inline';
              img-src 'self' data:;
              font-src 'self';
              connect-src 'self' ${process.env.NEXT_PUBLIC_API_URL};
              media-src 'self';
              object-src 'none';
              base-uri 'self';
              form-action 'self';
              frame-ancestors 'none';
              block-all-mixed-content;
              upgrade-insecure-requests;
            `.replace(/\s{2,}/g, ' ').trim()
          },
        ],
      },
    ];
  },
};

export default nextConfig;