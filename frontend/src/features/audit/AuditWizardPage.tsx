import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { CheckCircle2, Loader2, XCircle, ShieldCheck } from "lucide-react";
import { auditApi } from "@/services/auditApi";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ErrorState } from "@/components/States";

const AUDITED_SERVICES = [
  "IAM", "S3", "EC2", "CloudTrail", "CloudWatch", "Lambda", "RDS", "KMS", "Secrets Manager",
];

export function AuditWizardPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const navigate = useNavigate();
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const { data: audit, isError } = useQuery({
    queryKey: ["audit-status", auditId],
    queryFn: () => auditApi.getStatus(auditId!),
    enabled: !!auditId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1500;
    },
  });

  useEffect(() => {
    if (audit?.status === "completed" || audit?.status === "failed") return;
    const interval = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [audit?.status]);

  if (isError) {
    return <ErrorState description="We couldn't check on this audit's progress." />;
  }

  const status = audit?.status ?? "queued";

  return (
    <div className="mx-auto flex max-w-lg flex-col items-center gap-6 py-12">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent-blue/10">
        {status === "completed" ? (
          <CheckCircle2 className="h-8 w-8 text-accent-green" />
        ) : status === "failed" ? (
          <XCircle className="h-8 w-8 text-accent-red" />
        ) : (
          <Loader2 className="h-8 w-8 animate-spin text-accent-blue" />
        )}
      </div>

      <div className="text-center">
        <h1 className="text-xl font-semibold">
          {status === "completed"
            ? "Audit complete"
            : status === "failed"
              ? "Audit failed"
              : "Auditing your AWS environment"}
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          {status === "completed"
            ? `Scanned ${audit?.resources_scanned ?? 0} resources across 9 AWS services.`
            : status === "failed"
              ? "Something went wrong during collection. Check the account's IAM permissions and try again."
              : `Running IAM, S3, EC2, CloudTrail, CloudWatch, Lambda, RDS, KMS, and Secrets Manager checks — read-only, ${elapsedSeconds}s elapsed.`}
        </p>
      </div>

      {status !== "completed" && status !== "failed" && (
        <Card className="w-full">
          <div className="grid grid-cols-3 gap-2">
            {AUDITED_SERVICES.map((service) => (
              <motion.div
                key={service}
                initial={{ opacity: 0.4 }}
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 2, repeat: Infinity, delay: Math.random() * 1.5 }}
                className="flex items-center gap-2 rounded-lg border border-border bg-bg px-2 py-1.5 text-xs text-text-secondary"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-accent-blue" />
                {service}
              </motion.div>
            ))}
          </div>
        </Card>
      )}

      {status === "completed" && (
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate("/dashboard")}>
            View dashboard
          </Button>
          <Button onClick={() => navigate(`/findings?audit_session_id=${auditId}`)}>View findings</Button>
        </div>
      )}

      {status === "failed" && (
        <Button variant="secondary" onClick={() => navigate("/aws-accounts")}>
          Back to AWS accounts
        </Button>
      )}
    </div>
  );
}
