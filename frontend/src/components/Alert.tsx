import React from 'react';
import { AlertCircle, AlertTriangle, Info, CheckCircle, X } from 'lucide-react';
import { motion } from 'framer-motion';

interface AlertProps {
  type: 'error' | 'warning' | 'info' | 'success';
  title?: string;
  message: string;
  details?: Record<string, any>;
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
  dismissible = true,
}) => {
  const styles = {
    error: {
      border: 'border-red-500/30',
      bg: 'bg-red-500/10',
      icon: AlertCircle,
      iconColor: 'text-red-400',
      titleColor: 'text-red-300',
      btnBg: 'bg-red-500/20 hover:bg-red-500/30 text-red-300',
    },
    warning: {
      border: 'border-yellow-500/30',
      bg: 'bg-yellow-500/10',
      icon: AlertTriangle,
      iconColor: 'text-yellow-400',
      titleColor: 'text-yellow-300',
      btnBg: 'bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-300',
    },
    info: {
      border: 'border-blue-500/30',
      bg: 'bg-blue-500/10',
      icon: Info,
      iconColor: 'text-blue-400',
      titleColor: 'text-blue-300',
      btnBg: 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-300',
    },
    success: {
      border: 'border-accent/30',
      bg: 'bg-accent/10',
      icon: CheckCircle,
      iconColor: 'text-accent',
      titleColor: 'text-accent',
      btnBg: 'bg-accent/20 hover:bg-accent/30 text-accent',
    },
  };

  const s = styles[type];
  const Icon = s.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
      className={`${s.bg} ${s.border} border rounded-xl p-4 flex gap-3 items-start`}
    >
      <Icon className={`${s.iconColor} w-5 h-5 flex-shrink-0 mt-0.5`} />

      <div className="flex-1 min-w-0">
        {title && (
          <h3 className={`font-semibold text-sm mb-1 ${s.titleColor}`}>{title}</h3>
        )}
        <p className="text-sm text-sidebar-muted">{message}</p>

        {actionLabel && onAction && (
          <button
            onClick={onAction}
            className={`mt-3 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors ${s.btnBg}`}
          >
            {actionLabel}
          </button>
        )}
      </div>

      {dismissible && onDismiss && (
        <button
          onClick={onDismiss}
          className="flex-shrink-0 text-sidebar-muted hover:text-sidebar-text p-1 rounded-lg hover:bg-canvas-hover transition-colors"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </motion.div>
  );
};

export default Alert;
