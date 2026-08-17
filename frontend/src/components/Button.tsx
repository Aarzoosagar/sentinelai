import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import clsx from "clsx";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  isLoading?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary: "bg-accent-blue text-white hover:bg-blue-600 disabled:bg-blue-900",
  secondary: "bg-card border border-border text-text-primary hover:border-accent-blue/50",
  ghost: "bg-transparent text-text-secondary hover:text-text-primary hover:bg-card",
  danger: "bg-accent-red text-white hover:bg-red-600 disabled:bg-red-900",
};

const sizeClasses: Record<Size, string> = {
  sm: "text-xs px-2 py-1 gap-1",
  md: "text-sm px-3 py-2 gap-2",
  lg: "text-base px-4 py-3 gap-2",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", isLoading, disabled, className, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={clsx(
          "inline-flex items-center justify-center rounded-lg font-medium transition-colors duration-150",
          "disabled:cursor-not-allowed disabled:opacity-60",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      >
        {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
