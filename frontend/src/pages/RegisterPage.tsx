import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { AuthLayout } from "@/layouts/AuthLayout";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { useAuth } from "@/store/authStore";
import { isAxiosError } from "axios";

interface RegisterFormValues {
  full_name: string;
  email: string;
  password: string;
}

export function RegisterPage() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>();

  const onSubmit = async (values: RegisterFormValues) => {
    setServerError(null);
    try {
      await registerUser(values.email, values.password, values.full_name);
      navigate("/dashboard");
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 409) {
        setServerError("An account with this email already exists.");
      } else {
        setServerError("Something went wrong. Please try again.");
      }
    }
  };

  return (
    <AuthLayout>
      <h1 className="mb-1 text-xl font-semibold">Create your account</h1>
      <p className="mb-6 text-sm text-text-secondary">Start auditing your AWS environment in minutes.</p>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <Input
          label="Full name"
          autoComplete="name"
          error={errors.full_name?.message}
          {...register("full_name", { required: "Full name is required" })}
        />
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email", { required: "Email is required" })}
        />
        <Input
          label="Password"
          type="password"
          autoComplete="new-password"
          error={errors.password?.message}
          {...register("password", {
            required: "Password is required",
            minLength: { value: 8, message: "Password must be at least 8 characters" },
          })}
        />
        {serverError && <p className="text-sm text-accent-red">{serverError}</p>}
        <Button type="submit" isLoading={isSubmitting} className="mt-2 w-full">
          Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-text-secondary">
        Already have an account?{" "}
        <Link to="/login" className="text-accent-blue hover:underline">
          Log in
        </Link>
      </p>
    </AuthLayout>
  );
}
