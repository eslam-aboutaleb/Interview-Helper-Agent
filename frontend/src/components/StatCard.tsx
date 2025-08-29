import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: LucideIcon;
  color: 'blue' | 'green' | 'purple' | 'orange' | 'red';
  index: number;
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  color, 
  index 
}) => {
  const colorClasses = {
    blue: 'from-blue-500 to-blue-600 bg-blue-100',
    green: 'from-green-500 to-green-600 bg-green-100',
    purple: 'from-purple-500 to-purple-600 bg-purple-100',
    orange: 'from-orange-500 to-orange-600 bg-orange-100',
    red: 'from-red-500 to-red-600 bg-red-100',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
      className="bg-white rounded-2xl border border-gray-200 p-6 shadow-soft hover:shadow-medium transition-all duration-300 group"
      whileHover={{ y: -2 }}
    >
      <div className="flex items-center space-x-4">
        <motion.div 
          className={`p-3 ${colorClasses[color]} rounded-xl group-hover:scale-110 transition-transform duration-300`}
          whileHover={{ rotate: 5 }}
        >
          <Icon className="w-6 h-6 text-white" />
        </motion.div>
        <div className="flex-1">
          <motion.p 
            className="text-3xl font-bold text-gray-900 mb-1"
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: index * 0.1 + 0.2 }}
          >
            {value}
          </motion.p>
          <p className="text-sm font-medium text-gray-700">{title}</p>
          <p className="text-xs text-gray-500">{subtitle}</p>
        </div>
      </div>
    </motion.div>
  );
};

export default StatCard;