import { forwardRef, type InputHTMLAttributes } from "react";
import clsx from "clsx";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, id, ...props }, ref) => {
    const inputId = id ?? props.name;
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-text-secondary">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={clsx(
            "rounded-lg border bg-bg px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary/60",
            "transition-colors duration-150 focus:border-accent-blue focus:outline-none",
            error ? "border-accent-red" : "border-border",
            className
          )}
          {...props}
        />
        {error && <span className="text-xs text-accent-red">{error}</span>}
      </div>
    );
  }
);
Input.displayName = "Input";
