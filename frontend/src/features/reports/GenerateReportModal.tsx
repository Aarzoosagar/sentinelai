import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Modal } from "@/components/Modal";
import { Select } from "@/components/Select";
import { Button } from "@/components/Button";
import { reportsApi } from "@/services";
import { useToast } from "@/components/Toast";
import type { ReportCategory, ReportType } from "@/types";

export function GenerateReportModal({
  isOpen,
  onClose,
  auditId,
}: {
  isOpen: boolean;
  onClose: () => void;
  auditId: string;
}) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [type, setType] = useState<ReportType>("pdf");
  const [category, setCategory] = useState<ReportCategory>("executive");

  const mutation = useMutation({
    mutationFn: () => reportsApi.generate(auditId, type, category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports", auditId] });
      onClose();
      showToast("Report generated.", "success");
    },
  });

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Generate report">
      <div className="flex flex-col gap-4">
        <Select label="Format" value={type} onChange={(e) => setType(e.target.value as ReportType)}>
          <option value="pdf">PDF</option>
          <option value="csv">CSV</option>
          <option value="json">JSON</option>
        </Select>
        <Select label="Category" value={category} onChange={(e) => setCategory(e.target.value as ReportCategory)}>
          <option value="executive">Executive</option>
          <option value="technical">Technical</option>
          <option value="compliance">Compliance</option>
          <option value="risk">Risk</option>
          <option value="audit_history">Audit History</option>
        </Select>

        {mutation.isError && (
          <p className="text-sm text-accent-red">Couldn&apos;t generate the report. Please try again.</p>
        )}

        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button isLoading={mutation.isPending} onClick={() => mutation.mutate()}>
            Generate
          </Button>
        </div>
      </div>
    </Modal>
  );
}
