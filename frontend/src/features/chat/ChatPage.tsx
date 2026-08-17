import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Send, Sparkles } from "lucide-react";
import { auditApi } from "@/services/auditApi";
import { chatApi } from "@/services";
import { Select } from "@/components/Select";
import { LoadingState, EmptyState } from "@/components/States";
import { Card } from "@/components/Card";
import { ChatBubble } from "@/features/chat/ChatBubble";

export function ChatPage() {
  const { data: audits, isLoading: auditsLoading } = useQuery({
    queryKey: ["audit-history"],
    queryFn: auditApi.history,
  });
  const completedAudits = audits?.filter((a) => a.status === "completed") ?? [];

  const [auditId, setAuditId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!auditId && completedAudits.length > 0) setAuditId(completedAudits[0].id);
  }, [completedAudits, auditId]);

  const { data: history } = useQuery({
    queryKey: ["chat-history", auditId],
    queryFn: () => chatApi.history(auditId!),
    enabled: !!auditId,
  });

  const { data: suggestions } = useQuery({
    queryKey: ["suggested-questions"],
    queryFn: chatApi.suggestedQuestions,
  });

  const sendMutation = useMutation({
    mutationFn: (message: string) => chatApi.sendMessage(auditId!, message),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["chat-history", auditId] }),
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, sendMutation.isPending]);

  const handleSend = (message: string) => {
    if (!message.trim() || !auditId) return;
    setDraft("");
    sendMutation.mutate(message.trim());
  };

  if (auditsLoading) return <LoadingState label="Loading audits..." />;

  if (completedAudits.length === 0) {
    return (
      <EmptyState
        title="No completed audits yet"
        description="Run an audit first, then come back to ask SentinelAI's assistant about your findings."
      />
    );
  }

  const messages = history?.messages ?? [];

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">AI Security Chat</h1>
          <p className="text-sm text-text-secondary">Ask about findings — answers are grounded in this audit only.</p>
        </div>
        <Select value={auditId ?? ""} onChange={(e) => setAuditId(e.target.value)} className="w-64">
          {completedAudits.map((audit) => (
            <option key={audit.id} value={audit.id}>
              Audit from {new Date(audit.completed_at ?? audit.created_at).toLocaleString()}
            </option>
          ))}
        </Select>
      </div>

      <Card className="flex flex-1 flex-col overflow-hidden p-0">
        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
              <Sparkles className="h-8 w-8 text-accent-blue" />
              <p className="max-w-sm text-sm text-text-secondary">
                Ask about specific findings, request remediation steps, or get a summary of this audit.
              </p>
              {suggestions && suggestions.length > 0 && (
                <div className="flex flex-wrap justify-center gap-2">
                  {suggestions.map((s) => (
                    <button
                      key={s.prompt}
                      onClick={() => handleSend(s.prompt)}
                      className="rounded-full border border-border px-3 py-1.5 text-xs text-text-secondary hover:border-accent-blue/50 hover:text-text-primary"
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {messages.map((m) => (
                <ChatBubble key={m.id} message={m} />
              ))}
              {sendMutation.isPending && (
                <ChatBubble
                  message={{ id: "pending", role: "assistant", content: "Thinking...", created_at: new Date().toISOString() }}
                />
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend(draft);
          }}
          className="flex items-center gap-2 border-t border-border p-3"
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about this audit's findings..."
            className="flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm placeholder:text-text-secondary/60 focus:border-accent-blue focus:outline-none"
          />
          <button
            type="submit"
            disabled={!draft.trim() || sendMutation.isPending}
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-blue text-white disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </Card>
    </div>
  );
}
