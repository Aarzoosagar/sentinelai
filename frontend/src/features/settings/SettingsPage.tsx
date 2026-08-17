import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { settingsApi } from "@/services";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { LoadingState, ErrorState } from "@/components/States";

function Toggle({ checked, onChange, label, description }: { checked: boolean; onChange: (v: boolean) => void; label: string; description: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2">
      <div>
        <div className="text-sm font-medium">{label}</div>
        <div className="text-xs text-text-secondary">{description}</div>
      </div>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-6 w-11 shrink-0 rounded-full transition-colors duration-150 ${checked ? "bg-accent-blue" : "bg-white/10"}`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform duration-150 ${checked ? "translate-x-[22px]" : "translate-x-0.5"}`}
        />
      </button>
    </div>
  );
}

export function SettingsPage() {
  const queryClient = useQueryClient();
  const { data: settings, isLoading, isError } = useQuery({
    queryKey: ["settings"],
    queryFn: settingsApi.get,
  });

  const [groqModel, setGroqModel] = useState("");
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [criticalAlerts, setCriticalAlerts] = useState(true);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (settings) {
      setGroqModel(settings.groq_model_override ?? "");
      setEmailAlerts(settings.email_notifications_enabled);
      setCriticalAlerts(settings.critical_finding_alerts_enabled);
    }
  }, [settings]);

  const mutation = useMutation({
    mutationFn: () =>
      settingsApi.update({
        groq_model_override: groqModel || null,
        email_notifications_enabled: emailAlerts,
        critical_finding_alerts_enabled: criticalAlerts,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    },
  });

  if (isLoading) return <LoadingState label="Loading settings..." />;
  if (isError) return <ErrorState description="We couldn't load your settings." />;

  return (
    <div className="flex max-w-lg flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Settings</h1>
        <p className="text-sm text-text-secondary">Configure AI behavior and notification preferences.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>AI Model</CardTitle>
        </CardHeader>
        <Input
          label="Groq model override"
          placeholder="Leave blank to use the account default"
          value={groqModel}
          onChange={(e) => setGroqModel(e.target.value)}
        />
        <p className="mt-2 text-xs text-text-secondary">
          Overrides the default Groq model used for explanations, summaries, and chat in your account.
        </p>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
        </CardHeader>
        <div className="divide-y divide-border">
          <Toggle
            checked={emailAlerts}
            onChange={setEmailAlerts}
            label="Email notifications"
            description="Get notified by email when an audit completes."
          />
          <Toggle
            checked={criticalAlerts}
            onChange={setCriticalAlerts}
            label="Critical finding alerts"
            description="Get notified immediately when a critical-severity finding is detected."
          />
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
        </CardHeader>
        <p className="text-sm text-text-secondary">
          SentinelAI is dark mode only, matching the enterprise security tooling it&apos;s designed to sit alongside.
        </p>
      </Card>

      <div className="flex items-center gap-3">
        <Button onClick={() => mutation.mutate()} isLoading={mutation.isPending}>
          Save settings
        </Button>
        {saved && <span className="text-sm text-accent-green">Saved.</span>}
      </div>
    </div>
  );
}
