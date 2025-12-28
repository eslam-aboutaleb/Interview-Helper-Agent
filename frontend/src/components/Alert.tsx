import React from 'react';
import { AlertCircle, AlertTriangle, Info, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

interface AlertProps {
  type: 'error' | 'warning' | 'info' | 'success';
  title?: string;
  message: string;
  onDismiss?: () => void;
  actionLabel?: string;
  onAction?: () => void;
  dismissible?: boolean;
}

const Alert: React.FC<AlertProps> = ({
  type,
  title,
  message,
  onDismiss,
  actionLabel,
  onAction,
  dismissible = true
}) => {
  const styles = {
    error: {
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      iconColor: 'text-red-600',
      icon: AlertCircle,
      buttonColor: 'hover:bg-red-100'
    },
    warning: {
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
      iconColor: 'text-yellow-600',
      icon: AlertTriangle,
      buttonColor: 'hover:bg-yellow-100'
    },
    info: {
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      iconColor: 'text-blue-600',
      icon: Info,
      buttonColor: 'hover:bg-blue-100'
    },
    success: {
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      iconColor: 'text-green-600',
      icon: CheckCircle,
      buttonColor: 'hover:bg-green-100'
    }
  };

  const style = styles[type];
  const IconComponent = style.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.2 }}
      className={`${style.bgColor} ${style.borderColor} border rounded-lg p-4 flex gap-4 items-start`}
    >
      <IconComponent className={`${style.iconColor} w-5 h-5 flex-shrink-0 mt-0.5`} />

      <div className="flex-1 min-w-0">
        {title && (
          <h3 className={`font-semibold text-gray-900 mb-1 ${type === 'error' ? 'text-red-900' : ''}`}>
            {title}
          </h3>
        )}
        <p className="text-sm text-gray-700">{message}</p>

        {actionLabel && onAction && (
          <button
            onClick={onAction}
            className={`mt-3 text-sm font-medium text-gray-700 hover:text-gray-900 ${style.buttonColor} px-3 py-1.5 rounded transition-colors`}
          >
            {actionLabel}
          </button>
        )}
      </div>

      {dismissible && onDismiss && (
        <button
          onClick={onDismiss}
          className={`flex-shrink-0 text-gray-400 hover:text-gray-600 ${style.buttonColor} p-1 rounded transition-colors`}
          aria-label="Dismiss"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      )}
    </motion.div>
  );
};

export default Alert;
