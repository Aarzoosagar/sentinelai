import { useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { Modal } from "@/components/Modal";
import { Input } from "@/components/Input";
import { Select } from "@/components/Select";
import { Button } from "@/components/Button";
import { awsApi, type ConnectAccountPayload } from "@/services/awsApi";
import { useToast } from "@/components/Toast";
import type { AwsAuthMethod } from "@/types";

interface FormValues {
  account_alias: string;
  aws_account_id: string;
  region: string;
  auth_method: AwsAuthMethod;
  role_arn?: string;
  external_id?: string;
  access_key_id?: string;
  secret_access_key?: string;
}

export function ConnectAccountModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ defaultValues: { auth_method: "assume_role", region: "us-east-1" } });

  const authMethod = watch("auth_method");

  const mutation = useMutation({
    mutationFn: (payload: ConnectAccountPayload) => awsApi.connect(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["aws-accounts"] });
      reset();
      onClose();
      showToast("AWS account connected.", "success");
    },
    onError: (err) => {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setServerError(String(err.response.data.detail));
      } else {
        setServerError("Couldn't connect this account. Please check the details and try again.");
      }
    },
  });

  const onSubmit = (values: FormValues) => {
    setServerError(null);
    mutation.mutate(values as ConnectAccountPayload);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Connect an AWS account">
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <p className="text-xs text-text-secondary">
          SentinelAI only ever requests read-only access. It cannot create, modify, or delete any
          resource in your AWS account.
        </p>

        <Input
          label="Account alias"
          placeholder="e.g. Production"
          error={errors.account_alias?.message}
          {...register("account_alias", { required: "Give this account a name" })}
        />
        <Input
          label="AWS account ID"
          placeholder="123456789012"
          error={errors.aws_account_id?.message}
          {...register("aws_account_id", {
            required: "AWS account ID is required",
            pattern: { value: /^\d{12}$/, message: "Must be exactly 12 digits" },
          })}
        />
        <Input
          label="Region"
          placeholder="us-east-1"
          error={errors.region?.message}
          {...register("region", { required: "Region is required" })}
        />
        <Select label="Authentication method" {...register("auth_method")}>
          <option value="assume_role">AssumeRole (recommended)</option>
          <option value="access_key">Access keys</option>
        </Select>

        {authMethod === "assume_role" ? (
          <>
            <Input
              label="Role ARN"
              placeholder="arn:aws:iam::123456789012:role/SentinelAIReadOnly"
              error={errors.role_arn?.message}
              {...register("role_arn", { required: "Role ARN is required for AssumeRole" })}
            />
            <Input
              label="External ID (optional)"
              {...register("external_id")}
            />
          </>
        ) : (
          <>
            <Input
              label="Access key ID"
              error={errors.access_key_id?.message}
              {...register("access_key_id", { required: "Access key ID is required" })}
            />
            <Input
              label="Secret access key"
              type="password"
              error={errors.secret_access_key?.message}
              {...register("secret_access_key", { required: "Secret access key is required" })}
            />
          </>
        )}

        {serverError && <p className="text-sm text-accent-red">{serverError}</p>}

        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting || mutation.isPending}>
            Connect account
          </Button>
        </div>
      </form>
    </Modal>
  );
}
