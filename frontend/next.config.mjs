const nextConfig = {
  async rewrites() {
    // APP_URL is injected by Vercel at runtime via the service binding.
    // Falls back to localhost for local development (run backend on port 8000).
    const backendUrl = process.env.APP_URL ?? "http://127.0.0.1:8000";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};
export default nextConfig;
