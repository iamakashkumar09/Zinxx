import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root to this directory — a stray package-lock.json in
  // C:\Users\Aditya was otherwise making Next.js guess wrong.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
