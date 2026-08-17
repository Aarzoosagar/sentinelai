import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { AppShell } from "@/layouts/AppShell";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { AwsAccountsPage } from "@/features/aws/AwsAccountsPage";
import { AuditWizardPage } from "@/features/audit/AuditWizardPage";
import { FindingsListPage } from "@/features/findings/FindingsListPage";
import { FindingDetailPage } from "@/features/findings/FindingDetailPage";
import { CompliancePage } from "@/features/compliance/CompliancePage";
import { ReportsPage } from "@/features/reports/ReportsPage";
import { ChatPage } from "@/features/chat/ChatPage";
import { AuditHistoryPage } from "@/features/audit/AuditHistoryPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { ProfilePage } from "@/pages/ProfilePage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/aws-accounts" element={<AwsAccountsPage />} />
          <Route path="/audit-wizard/:auditId" element={<AuditWizardPage />} />
          <Route path="/findings" element={<FindingsListPage />} />
          <Route path="/findings/:findingId" element={<FindingDetailPage />} />
          <Route path="/compliance" element={<CompliancePage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/audit-history" element={<AuditHistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
