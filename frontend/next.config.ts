import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Không proxy API qua Next: frontend gọi thẳng backend bằng NEXT_PUBLIC_API_BASE_URL
  // để giữ luồng SSE không bị buffer thêm một lớp.
};

export default nextConfig;
