import { api } from "@/services/api";
import type {
  ChatMessage,
  ComplianceOverview,
  DashboardSummary,
  Report,
  ReportCategory,
  ReportType,
  SuggestedQuestion,
  UserSettings,
} from "@/types";

export const complianceApi = {
  overview: (auditId: string) => api.get<ComplianceOverview>(`/compliance/${auditId}`).then((r) => r.data),
};

export const reportsApi = {
  generate: (auditSessionId: string, type: ReportType, category: ReportCategory) =>
    api
      .post<Report>("/reports/generate", { audit_session_id: auditSessionId, type, category })
      .then((r) => r.data),
  listForAudit: (auditId: string) => api.get<Report[]>(`/reports/audit/${auditId}`).then((r) => r.data),
  downloadUrl: (reportId: string) => `/api/v1/reports/${reportId}/download`,
};

export const chatApi = {
  suggestedQuestions: () => api.get<SuggestedQuestion[]>("/chat/suggested-questions").then((r) => r.data),
  history: (auditId: string) =>
    api.get<{ audit_session_id: string; messages: ChatMessage[] }>(`/chat/${auditId}/history`).then((r) => r.data),
  sendMessage: (auditSessionId: string, message: string) =>
    api
      .post<ChatMessage>("/chat/message", { audit_session_id: auditSessionId, message })
      .then((r) => r.data),
};

export const dashboardApi = {
  summary: () => api.get<DashboardSummary>("/dashboard/summary").then((r) => r.data),
};

export const settingsApi = {
  get: () => api.get<UserSettings>("/settings").then((r) => r.data),
  update: (payload: Partial<UserSettings>) => api.patch<UserSettings>("/settings", payload).then((r) => r.data),
};

export const profileApi = {
  update: (payload: { full_name?: string; current_password?: string; new_password?: string }) =>
    api.patch("/profile", payload).then((r) => r.data),
};
