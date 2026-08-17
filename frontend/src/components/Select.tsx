import { forwardRef, type SelectHTMLAttributes } from "react";
import clsx from "clsx";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, className, id, children, ...props }, ref) => {
    const selectId = id ?? props.name;
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={selectId} className="text-sm font-medium text-text-secondary">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={clsx(
            "rounded-lg border bg-bg px-3 py-2 text-sm text-text-primary",
            "transition-colors duration-150 focus:border-accent-blue focus:outline-none",
            error ? "border-accent-red" : "border-border",
            className
          )}
          {...props}
        >
          {children}
        </select>
        {error && <span className="text-xs text-accent-red">{error}</span>}
      </div>
    );
  }
);
Select.displayName = "Select";
