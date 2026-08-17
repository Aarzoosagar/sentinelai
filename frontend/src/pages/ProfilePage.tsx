import { useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { useAuth } from "@/store/authStore";
import { profileApi } from "@/services";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";

interface ProfileFormValues {
  full_name: string;
}

interface PasswordFormValues {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export function ProfilePage() {
  const { user } = useAuth();
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const {
    register: registerProfile,
    handleSubmit: handleProfileSubmit,
    formState: { isSubmitting: isProfileSubmitting },
  } = useForm<ProfileFormValues>({ defaultValues: { full_name: user?.full_name ?? "" } });

  const {
    register: registerPassword,
    handleSubmit: handlePasswordSubmit,
    reset: resetPasswordForm,
    formState: { errors: passwordErrors, isSubmitting: isPasswordSubmitting },
  } = useForm<PasswordFormValues>();

  const profileMutation = useMutation({
    mutationFn: (values: ProfileFormValues) => profileApi.update(values),
    onSuccess: () => {
      setProfileSuccess(true);
      setTimeout(() => setProfileSuccess(false), 2500);
    },
  });

  const passwordMutation = useMutation({
    mutationFn: (values: { current_password: string; new_password: string }) => profileApi.update(values),
    onSuccess: () => {
      setPasswordSuccess(true);
      setPasswordError(null);
      resetPasswordForm();
      setTimeout(() => setPasswordSuccess(false), 2500);
    },
    onError: (err) => {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setPasswordError(String(err.response.data.detail));
      } else {
        setPasswordError("Couldn't update your password. Please try again.");
      }
    },
  });

  const onPasswordSubmit = (values: PasswordFormValues) => {
    setPasswordError(null);
    if (values.new_password !== values.confirm_password) {
      setPasswordError("New password and confirmation don't match.");
      return;
    }
    passwordMutation.mutate({ current_password: values.current_password, new_password: values.new_password });
  };

  return (
    <div className="flex max-w-lg flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Profile</h1>
        <p className="text-sm text-text-secondary">Manage your account details.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Account details</CardTitle>
        </CardHeader>
        <form
          onSubmit={handleProfileSubmit((values) => profileMutation.mutate(values))}
          className="flex flex-col gap-4"
        >
          <Input label="Email" value={user?.email ?? ""} disabled />
          <Input label="Full name" {...registerProfile("full_name", { required: true })} />
          {profileSuccess && <p className="text-sm text-accent-green">Profile updated.</p>}
          <Button type="submit" isLoading={isProfileSubmitting || profileMutation.isPending} className="w-fit">
            Save changes
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Change password</CardTitle>
        </CardHeader>
        <form onSubmit={handlePasswordSubmit(onPasswordSubmit)} className="flex flex-col gap-4">
          <Input
            label="Current password"
            type="password"
            error={passwordErrors.current_password?.message}
            {...registerPassword("current_password", { required: "Current password is required" })}
          />
          <Input
            label="New password"
            type="password"
            error={passwordErrors.new_password?.message}
            {...registerPassword("new_password", {
              required: "New password is required",
              minLength: { value: 8, message: "Must be at least 8 characters" },
            })}
          />
          <Input
            label="Confirm new password"
            type="password"
            error={passwordErrors.confirm_password?.message}
            {...registerPassword("confirm_password", { required: "Please confirm your new password" })}
          />
          {passwordError && <p className="text-sm text-accent-red">{passwordError}</p>}
          {passwordSuccess && <p className="text-sm text-accent-green">Password updated.</p>}
          <Button type="submit" isLoading={isPasswordSubmitting || passwordMutation.isPending} className="w-fit">
            Update password
          </Button>
        </form>
      </Card>
    </div>
  );
}
