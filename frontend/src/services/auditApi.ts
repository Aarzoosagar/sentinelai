import { api } from "@/services/api";
import type { AuditSession } from "@/types";

export const auditApi = {
  start: (awsAccountId: string) =>
    api.post<AuditSession>("/audit/start", { aws_account_id: awsAccountId }).then((r) => r.data),
  getStatus: (auditId: string) =>
    api.get<{ id: string; status: string; resources_scanned: number }>(`/audit/${auditId}/status`).then((r) => r.data),
  get: (auditId: string) => api.get<AuditSession>(`/audit/${auditId}`).then((r) => r.data),
  history: () => api.get<AuditSession[]>("/audit/history/all").then((r) => r.data),
};
