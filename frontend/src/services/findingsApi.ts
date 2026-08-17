import { api } from "@/services/api";
import type {
  AwsService,
  FindingDetail,
  FindingListItem,
  FindingStatus,
  PaginatedResponse,
  Severity,
} from "@/types";

export interface FindingsFilters {
  audit_session_id?: string;
  severity?: Severity;
  service?: AwsService;
  status?: FindingStatus;
  region?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export const findingsApi = {
  list: (filters: FindingsFilters) =>
    api.get<PaginatedResponse<FindingListItem>>("/findings", { params: filters }).then((r) => r.data),
  get: (findingId: string) => api.get<FindingDetail>(`/findings/${findingId}`).then((r) => r.data),
  updateStatus: (findingId: string, status: FindingStatus) =>
    api.patch<FindingDetail>(`/findings/${findingId}/status`, { status }).then((r) => r.data),
  explain: (findingId: string) =>
    api
      .post<{ finding_id: string; ai_explanation: string; generated_fresh: boolean }>(
        `/findings/${findingId}/ai-explain`
      )
      .then((r) => r.data),
  iacExample: (findingId: string, format: "cli" | "terraform" | "cloudformation") =>
    api
      .get<{ finding_id: string; format: string; snippet: string }>(`/findings/${findingId}/iac-example`, {
        params: { format },
      })
      .then((r) => r.data),
};
