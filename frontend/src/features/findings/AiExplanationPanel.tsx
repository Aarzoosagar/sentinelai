import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/Button";
import { findingsApi } from "@/services/findingsApi";
import type { FindingDetail } from "@/types";

export function AiExplanationPanel({ finding }: { finding: FindingDetail }) {
  const queryClient = useQueryClient();
  const [explanation, setExplanation] = useState(finding.ai_explanation);

  const mutation = useMutation({
    mutationFn: () => findingsApi.explain(finding.id),
    onSuccess: (result) => {
      setExplanation(result.ai_explanation);
      queryClient.invalidateQueries({ queryKey: ["finding", finding.id] });
    },
  });

  if (!explanation) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border py-8 text-center">
        <Sparkles className="h-6 w-6 text-accent-blue" />
        <p className="max-w-sm text-sm text-text-secondary">
          Ask SentinelAI's assistant to explain why this finding matters, how it could be exploited, and what to do about it.
        </p>
        <Button size="sm" onClick={() => mutation.mutate()} isLoading={mutation.isPending}>
          {mutation.isPending ? "Generating explanation..." : "Explain this finding"}
        </Button>
        {mutation.isError && <p className="text-xs text-accent-red">Couldn&apos;t generate an explanation. Try again.</p>}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-accent-blue/20 bg-accent-blue/5 p-4">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-accent-blue">
        <Sparkles className="h-3.5 w-3.5" /> AI Explanation
      </div>
      <div className="whitespace-pre-line text-sm text-text-primary">{explanation}</div>
      {mutation.isPending && (
        <div className="mt-2 flex items-center gap-2 text-xs text-text-secondary">
          <Loader2 className="h-3 w-3 animate-spin" /> Refreshing...
        </div>
      )}
    </div>
  );
}
