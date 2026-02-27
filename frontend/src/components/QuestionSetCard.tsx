import React from 'react';
import { motion } from 'framer-motion';
import { FolderOpen, MessageSquare, Briefcase } from 'lucide-react';

interface QuestionSetCardProps {
  id: number;
  name: string;
  description: string;
  jobTitle: string;
  questionCount: number;
  onSelect?: () => void;
}

const QuestionSetCard: React.FC<QuestionSetCardProps> = ({
  id,
  name,
  description,
  jobTitle,
  questionCount,
  onSelect,
}) => {
  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ duration: 0.15 }}
      className="bg-canvas-surface border border-canvas-border rounded-xl p-5 hover:border-canvas-hover transition-colors duration-200 flex flex-col"
    >
      {/* Icon + title */}
      <div className="flex items-start gap-3 mb-3">
        <div className="p-2.5 bg-accent/15 rounded-lg flex-shrink-0">
          <FolderOpen className="w-5 h-5 text-accent" />
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-sidebar-text truncate">{name}</h3>
          <div className="flex items-center gap-1.5 mt-0.5">
            <Briefcase className="w-3.5 h-3.5 text-sidebar-muted flex-shrink-0" />
            <span className="text-xs text-sidebar-muted truncate">{jobTitle}</span>
          </div>
        </div>
      </div>

      {/* Description */}
      {description && (
        <p className="text-xs text-sidebar-muted leading-relaxed mb-4 flex-1 line-clamp-2">
          {description}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-auto pt-3 border-t border-canvas-border">
        <div className="flex items-center gap-1.5 text-xs text-sidebar-muted">
          <MessageSquare className="w-3.5 h-3.5" />
          <span>{questionCount} questions</span>
        </div>
        {onSelect && (
          <button
            onClick={onSelect}
            className="text-xs font-medium text-accent hover:text-accent-hover transition-colors"
          >
            View →
          </button>
        )}
      </div>
    </motion.div>
  );
};

export default QuestionSetCard;
