import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
    return (
      <div className="w-full">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-semibold text-slate-700 mb-2">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`w-full px-4 py-3 rounded-xl border bg-slate-50 focus:bg-white transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 disabled:opacity-50 disabled:cursor-not-allowed ${
            error ? 'border-red-300 focus:ring-red-400 focus:border-red-400' : 'border-slate-300'
          } ${className}`}
          {...props}
        />
        {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
