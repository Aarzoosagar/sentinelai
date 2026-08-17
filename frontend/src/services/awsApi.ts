import { api } from "@/services/api";
import type { AwsAccount, AwsAuthMethod } from "@/types";

export interface ConnectAccountPayload {
  account_alias: string;
  aws_account_id: string;
  region: string;
  auth_method: AwsAuthMethod;
  role_arn?: string;
  external_id?: string;
  access_key_id?: string;
  secret_access_key?: string;
}

export interface ValidationResult {
  account_id: string;
  validation_status: string;
  caller_identity_arn: string | null;
  error: string | null;
}

export const awsApi = {
  connect: (payload: ConnectAccountPayload) =>
    api.post<AwsAccount>("/aws/accounts", payload).then((r) => r.data),
  list: () => api.get<AwsAccount[]>("/aws/accounts").then((r) => r.data),
  get: (accountId: string) => api.get<AwsAccount>(`/aws/accounts/${accountId}`).then((r) => r.data),
  validate: (accountId: string) =>
    api.post<ValidationResult>(`/aws/accounts/${accountId}/validate`).then((r) => r.data),
};
