import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, XCircle, Clock, Cloud } from "lucide-react";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { StatusChip } from "@/components/Badge";
import { awsApi } from "@/services/awsApi";
import type { AwsAccount } from "@/types";

const STATUS_CONFIG: Record<string, { icon: typeof CheckCircle2; tone: "success" | "danger" | "neutral"; label: string }> = {
  valid: { icon: CheckCircle2, tone: "success", label: "Valid" },
  invalid: { icon: XCircle, tone: "danger", label: "Invalid" },
  pending: { icon: Clock, tone: "neutral", label: "Pending" },
};

export function AwsAccountCard({ account, onStartAudit }: { account: AwsAccount; onStartAudit: (accountId: string) => void }) {
  const queryClient = useQueryClient();
  const config = STATUS_CONFIG[account.validation_status];
  const Icon = config.icon;

  const validateMutation = useMutation({
    mutationFn: () => awsApi.validate(account.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["aws-accounts"] }),
  });

  return (
    <Card>
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-blue/10 text-accent-blue">
            <Cloud className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <div className="truncate font-medium">{account.account_alias}</div>
            <div className="sentinel-mono truncate text-xs text-text-secondary">{account.aws_account_id}</div>
          </div>
        </div>
        <span className="shrink-0">
          <StatusChip tone={config.tone}>
            <Icon className="mr-1 inline h-3 w-3" />
            {config.label}
          </StatusChip>
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-secondary">
        <span>Region: {account.region}</span>
        <span>Auth: {account.auth_method === "assume_role" ? "AssumeRole" : "Access keys"}</span>
        {account.validated_at && <span>Last validated: {new Date(account.validated_at).toLocaleString()}</span>}
      </div>

      <div className="mt-4 flex gap-2">
        <Button size="sm" variant="secondary" isLoading={validateMutation.isPending} onClick={() => validateMutation.mutate()}>
          Validate
        </Button>
        <Button size="sm" onClick={() => onStartAudit(account.id)} disabled={account.validation_status !== "valid"}>
          Start audit
        </Button>
      </div>
    </Card>
  );
}
