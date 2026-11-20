import type { NextConfig } from "next";

// HUB-1: built with NEXT_PUBLIC_BASE_PATH (e.g. "/posture") the app is
// served under the hub URL through the CRM project's rewrites. Unset = the
// app's own URL at "/", exactly as before.
const basePath = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/+$/, "");
const hubOrigin = (process.env.NEXT_PUBLIC_HUB_ORIGIN || "").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  ...(basePath ? { basePath } : {}),
  async redirects() {
    if (!basePath || !hubOrigin) return [];
    // The old standalone URL (no base path) sends people to the hub.
    return [{ source: "/", destination: `${hubOrigin}${basePath}`, basePath: false, permanent: false }];
  },
};

export default nextConfig;
