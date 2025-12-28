import React from 'react';
import { motion } from 'framer-motion';
import { Package, RefreshCw } from 'lucide-react';

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
  actionLoading = false
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex items-center justify-center min-h-96 px-4"
    >
      <div className="text-center max-w-md">
        <div className="flex justify-center mb-4">
          <div className="p-6 bg-gray-100 rounded-full">
            {icon || <Package className="w-12 h-12 text-gray-400" />}
          </div>
        </div>

        <h3 className="text-2xl font-bold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{message}</p>

        {actionLabel && onAction && (
          <motion.button
            onClick={onAction}
            disabled={actionLoading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {actionLoading && (
              <RefreshCw className="w-4 h-4 animate-spin" />
            )}
            {actionLabel}
          </motion.button>
        )}
      </div>
    </motion.div>
  );
};

export default EmptyState;
