import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Copy, Check } from "lucide-react";
import clsx from "clsx";
import { findingsApi } from "@/services/findingsApi";
import { LoadingState } from "@/components/States";

type Format = "cli" | "terraform" | "cloudformation";
const FORMATS: { id: Format; label: string }[] = [
  { id: "cli", label: "AWS CLI" },
  { id: "terraform", label: "Terraform" },
  { id: "cloudformation", label: "CloudFormation" },
];

export function IacExamplePanel({ findingId }: { findingId: string }) {
  const [format, setFormat] = useState<Format>("terraform");
  const [copied, setCopied] = useState(false);

  const { data, isFetching, isError } = useQuery({
    queryKey: ["iac-example", findingId, format],
    queryFn: () => findingsApi.iacExample(findingId, format),
    retry: false,
  });

  const handleCopy = async () => {
    if (!data?.snippet) return;
    await navigator.clipboard.writeText(data.snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {FORMATS.map((f) => (
            <button
              key={f.id}
              onClick={() => setFormat(f.id)}
              className={clsx(
                "rounded-md px-2.5 py-1 text-xs font-medium transition-colors duration-150",
                format === f.id ? "bg-accent-blue/10 text-accent-blue" : "text-text-secondary hover:bg-white/5"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <button
          onClick={handleCopy}
          disabled={!data?.snippet}
          className="flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary disabled:opacity-40"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-accent-green" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="mt-2 max-h-72 overflow-auto rounded-lg border border-border bg-bg p-3">
        {isFetching ? (
          <LoadingState label="Generating snippet..." />
        ) : isError ? (
          <p className="py-4 text-center text-sm text-text-secondary">
            Couldn&apos;t generate a code example right now. Try again in a moment.
          </p>
        ) : (
          <pre className="sentinel-mono whitespace-pre-wrap text-text-primary">{data?.snippet}</pre>
        )}
      </div>
    </div>
  );
}
