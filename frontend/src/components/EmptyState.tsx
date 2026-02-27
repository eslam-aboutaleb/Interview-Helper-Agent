import React from 'react';
import { motion } from 'framer-motion';
import { Package } from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';

interface EmptyStateProps {
  title: string;
  message: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  actionLoading?: boolean;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  message,
  icon,
  actionLabel,
  onAction,
  actionLoading = false,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex items-center justify-center min-h-64 px-4"
    >
      <div className="text-center max-w-sm">
        <div className="flex justify-center mb-5">
          <div className="p-5 bg-canvas-surface rounded-2xl border border-canvas-border">
            {icon || <Package className="w-10 h-10 text-sidebar-muted" />}
          </div>
        </div>

        <h3 className="text-lg font-semibold text-sidebar-text mb-2">{title}</h3>
        <p className="text-sm text-sidebar-muted mb-6 leading-relaxed">{message}</p>

        {actionLabel && onAction && (
          <motion.button
            onClick={onAction}
            disabled={actionLoading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent-hover text-white rounded-xl text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {actionLoading && <LoadingSpinner size="sm" />}
            {actionLabel}
          </motion.button>
        )}
      </div>
    </motion.div>
  );
};

export default EmptyState;
