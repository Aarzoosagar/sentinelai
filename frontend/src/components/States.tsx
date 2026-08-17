import clsx from "clsx";
import { Loader2, Inbox, AlertTriangle } from "lucide-react";

export function ProgressBar({ value, tone = "blue" }: { value: number; tone?: "blue" | "green" | "yellow" | "red" }) {
  const toneClasses: Record<string, string> = {
    blue: "bg-accent-blue",
    green: "bg-accent-green",
    yellow: "bg-accent-yellow",
    red: "bg-accent-red",
  };
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
      <div
        className={clsx("h-full rounded-full transition-all duration-300", toneClasses[tone])}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-text-secondary">
      <Loader2 className="h-6 w-6 animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border py-16 text-center">
      <Inbox className="h-8 w-8 text-text-secondary" />
      <div className="text-sm font-medium text-text-primary">{title}</div>
      {description && <div className="max-w-sm text-sm text-text-secondary">{description}</div>}
      {action}
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", description }: { title?: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-accent-red/30 bg-accent-red/5 py-16 text-center">
      <AlertTriangle className="h-8 w-8 text-accent-red" />
      <div className="text-sm font-medium text-text-primary">{title}</div>
      {description && <div className="max-w-sm text-sm text-text-secondary">{description}</div>}
    </div>
  );
}
