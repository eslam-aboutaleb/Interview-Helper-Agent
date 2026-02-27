import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: LucideIcon;
  color: 'blue' | 'green' | 'gray' | 'orange' | 'red';
  index: number;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon: Icon, color, index }) => {
  const iconColors = {
    blue: 'text-blue-400',
    green: 'text-accent',
    gray: 'text-sidebar-muted',
    orange: 'text-orange-400',
    red: 'text-red-400',
  };

  const iconBg = {
    blue: 'bg-blue-500/15',
    green: 'bg-accent/15',
    gray: 'bg-canvas-hover',
    orange: 'bg-orange-500/15',
    red: 'bg-red-500/15',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.08 }}
      className="bg-canvas-surface border border-canvas-border rounded-xl p-5 hover:border-canvas-hover transition-colors duration-200"
    >
      <div className="flex items-start justify-between mb-4">
        <div className={`p-2.5 ${iconBg[color]} rounded-lg`}>
          <Icon className={`w-5 h-5 ${iconColors[color]}`} />
        </div>
      </div>
      <p className="text-2xl font-bold text-sidebar-text mb-1">{value}</p>
      <p className="text-sm font-medium text-sidebar-text mb-0.5">{title}</p>
      <p className="text-xs text-sidebar-muted">{subtitle}</p>
    </motion.div>
  );
};

export default StatCard;
