import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { awsApi } from "@/services/awsApi";
import { auditApi } from "@/services/auditApi";
import { Button } from "@/components/Button";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { AwsAccountCard } from "@/features/aws/AwsAccountCard";
import { ConnectAccountModal } from "@/features/aws/ConnectAccountModal";

export function AwsAccountsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);

  const { data: accounts, isLoading, isError } = useQuery({
    queryKey: ["aws-accounts"],
    queryFn: awsApi.list,
  });

  const startAuditMutation = useMutation({
    mutationFn: (accountId: string) => auditApi.start(accountId),
    onSuccess: (audit) => {
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      navigate(`/audit-wizard/${audit.id}`);
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">AWS Accounts</h1>
          <p className="text-sm text-text-secondary">Connect an account to start auditing — read-only, always.</p>
        </div>
        <Button onClick={() => setModalOpen(true)}>
          <Plus className="h-4 w-4" /> Connect AWS account
        </Button>
      </div>

      {isLoading && <LoadingState label="Loading connected accounts..." />}
      {isError && <ErrorState description="We couldn't load your AWS accounts." />}

      {accounts && accounts.length === 0 && (
        <EmptyState
          title="No AWS accounts connected"
          description="Connect an account with a ReadOnly IAM role to start your first audit."
          action={
            <Button size="sm" onClick={() => setModalOpen(true)}>
              Connect AWS account
            </Button>
          }
        />
      )}

      {accounts && accounts.length > 0 && (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-4">
          {accounts.map((account) => (
            <AwsAccountCard
              key={account.id}
              account={account}
              onStartAudit={(id) => startAuditMutation.mutate(id)}
            />
          ))}
        </div>
      )}

      <ConnectAccountModal isOpen={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
}
