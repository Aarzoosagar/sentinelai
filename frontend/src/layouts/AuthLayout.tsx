import type { ReactNode } from "react";
import { ShieldCheck } from "lucide-react";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center justify-center gap-2">
          <ShieldCheck className="h-6 w-6 text-accent-blue" />
          <span className="text-lg font-semibold tracking-tight">SentinelAI</span>
        </div>
        <div className="sentinel-card p-6">{children}</div>
        <p className="mt-6 text-center text-xs text-text-secondary">
          AI-Powered AWS Cloud Security Auditor — read-only by design.
        </p>
      </div>
    </div>
  );
}
