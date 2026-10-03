import React from 'react';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width,
  height,
  className = '',
  ...props
}) => {
  const variantClasses = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-xl',
  };

  return (
    <div
      className={`animate-pulse bg-slate-200 ${variantClasses[variant]} ${className}`}
      style={{ width, height }}
      aria-hidden="true"
      {...props}
    />
  );
};

export const SkeletonCard: React.FC = () => (
  <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-soft space-y-4">
    <Skeleton width="40%" height={20} />
    <Skeleton width="100%" height={16} />
    <Skeleton width="80%" height={16} />
    <Skeleton width="60%" height={16} />
  </div>
);

export const SkeletonStatCard: React.FC = () => (
  <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-soft space-y-3">
    <Skeleton width="50%" height={14} />
    <Skeleton width="70%" height={32} />
    <Skeleton width="40%" height={12} />
  </div>
);
