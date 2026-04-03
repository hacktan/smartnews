import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ||
      "https://smartnews-api.victorioussea-ab137c42.eastus.azurecontainerapps.io",
  },
};

export default nextConfig;
