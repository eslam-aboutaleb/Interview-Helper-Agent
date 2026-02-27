import React from 'react';
import { motion } from 'framer-motion';
import { Flag, Trash2, Calendar, Tag, Loader2 } from 'lucide-react';
import { Question } from '../types';

interface QuestionCardProps {
  question: Question;
  isLoading?: boolean;
  onToggleFlag: (id: number) => void;
  onUpdateDifficulty: (id: number, difficulty: number) => void;
  onDelete: (id: number) => void;
  index: number;
}

const difficultyLabel = ['', 'Beginner', 'Easy', 'Medium', 'Hard', 'Expert'];
const difficultyColor = [
  '',
  'text-green-400 bg-green-400/10 border-green-400/20',
  'text-blue-400 bg-blue-400/10 border-blue-400/20',
  'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  'text-orange-400 bg-orange-400/10 border-orange-400/20',
  'text-red-400 bg-red-400/10 border-red-400/20',
];

const QuestionCard: React.FC<QuestionCardProps> = ({
  question,
  isLoading = false,
  onToggleFlag,
  onUpdateDifficulty,
  onDelete,
  index,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.04 }}
      className={`bg-canvas-surface border rounded-xl p-5 transition-colors duration-200 ${
        question.is_flagged ? 'border-yellow-500/30' : 'border-canvas-border hover:border-canvas-hover'
      }`}
    >
      {/* Top row: badges + actions */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Type badge */}
          <span
            className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${
              question.question_type === 'technical'
                ? 'text-blue-400 bg-blue-400/10 border-blue-400/20'
                : 'text-purple-400 bg-purple-400/10 border-purple-400/20'
            }`}
          >
            {question.question_type}
          </span>

          {/* Difficulty badge */}
          <span
            className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${
              difficultyColor[question.difficulty] || difficultyColor[3]
            }`}
          >
            {difficultyLabel[question.difficulty] || `Level ${question.difficulty}`}
          </span>

          {/* Job title */}
          <span className="px-2.5 py-0.5 rounded-full text-xs font-medium text-sidebar-muted bg-canvas-hover border border-canvas-border">
            {question.job_title}
          </span>

          {/* Flag indicator */}
          {question.is_flagged && (
            <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium text-yellow-400 bg-yellow-400/10 border border-yellow-400/20">
              <Flag className="w-3 h-3" />
              Flagged
            </span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Difficulty selector */}
          <select
            value={question.difficulty}
            onChange={(e) => onUpdateDifficulty(question.id, parseInt(e.target.value))}
            disabled={isLoading}
            aria-label={`Set difficulty for question ${question.id}`}
            className="text-xs bg-canvas-hover border border-canvas-border text-sidebar-muted rounded-lg px-2 py-1.5 focus:border-accent focus:outline-none disabled:opacity-50 cursor-pointer"
          >
            {[1, 2, 3, 4, 5].map((level) => (
              <option key={level} value={level}>
                {difficultyLabel[level]}
              </option>
            ))}
          </select>

          {/* Flag button */}
          <button
            onClick={() => onToggleFlag(question.id)}
            disabled={isLoading}
            aria-label={question.is_flagged ? 'Unflag question' : 'Flag question'}
            className={`p-1.5 rounded-lg transition-colors duration-150 ${
              question.is_flagged
                ? 'text-yellow-400 bg-yellow-400/10 hover:bg-yellow-400/20'
                : 'text-sidebar-muted hover:text-yellow-400 hover:bg-yellow-400/10'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Flag className="w-4 h-4" />
            )}
          </button>

          {/* Delete button */}
          <button
            onClick={() => onDelete(question.id)}
            disabled={isLoading}
            aria-label="Delete question"
            className="p-1.5 rounded-lg text-sidebar-muted hover:text-red-400 hover:bg-red-400/10 transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Question text */}
      <p className="text-sidebar-text text-sm leading-relaxed mb-4">{question.question_text}</p>

      {/* Tags */}
      {question.tags && (
        <div className="flex flex-wrap items-center gap-1.5 mb-3">
          <Tag className="w-3.5 h-3.5 text-sidebar-muted flex-shrink-0" />
          {question.tags.split(',').map((tag, i) => (
            <span
              key={i}
              className="px-2 py-0.5 bg-canvas-hover text-sidebar-muted rounded-md text-xs border border-canvas-border"
            >
              {tag.trim()}
            </span>
          ))}
        </div>
      )}

      {/* Date */}
      <div className="flex items-center gap-1.5 text-xs text-sidebar-muted">
        <Calendar className="w-3.5 h-3.5" />
        <span>{new Date(question.created_at).toLocaleDateString()}</span>
      </div>
    </motion.div>
  );
};

export default QuestionCard;
