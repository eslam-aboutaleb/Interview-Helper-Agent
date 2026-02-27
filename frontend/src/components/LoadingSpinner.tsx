import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-7 h-7 border-2',
    lg: 'w-10 h-10 border-2',
  };

  return (
    <div
      className={`${sizeClasses[size]} rounded-full border-canvas-border border-t-accent animate-spin ${className}`}
      role="status"
      aria-label="Loading"
    />
  );
};

export default LoadingSpinner;
