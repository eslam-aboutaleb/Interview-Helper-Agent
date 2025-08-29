import React from 'react';
import { motion } from 'framer-motion';
import { Flag, Trash2, Calendar, Tag } from 'lucide-react';
import { Question } from '../types';

interface QuestionCardProps {
  question: Question;
  onToggleFlag: (id: number) => void;
  onUpdateDifficulty: (id: number, difficulty: number) => void;
  onDelete: (id: number) => void;
  index: number;
}

const QuestionCard: React.FC<QuestionCardProps> = ({
  question,
  onToggleFlag,
  onUpdateDifficulty,
  onDelete,
  index,
}) => {
  const getDifficultyColor = (difficulty: number): string => {
    const colors = {
      1: 'bg-success-100 text-success-800 border-success-200',
      2: 'bg-primary-100 text-primary-800 border-primary-200',
      3: 'bg-warning-100 text-warning-800 border-warning-200',
      4: 'bg-error-100 text-error-800 border-error-200',
      5: 'bg-purple-100 text-purple-800 border-purple-200',
    };
    return colors[difficulty as keyof typeof colors] || colors[3];
  };

  const getTypeColor = (type: string): string => {
    return type === 'technical' 
      ? 'bg-blue-100 text-blue-800 border-blue-200'
      : 'bg-purple-100 text-purple-800 border-purple-200';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className="bg-white rounded-2xl border border-gray-200 p-6 shadow-soft hover:shadow-medium transition-all duration-300 group"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-4">
            <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getTypeColor(question.question_type)}`}>
              {question.question_type}
            </span>
            <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getDifficultyColor(question.difficulty)}`}>
              Level {question.difficulty}
            </span>
            <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm border border-gray-200">
              {question.job_title}
            </span>
            {question.is_flagged && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="flex items-center"
              >
                <Flag className="w-4 h-4 text-warning-500" />
              </motion.div>
            )}
          </div>
          
          <p className="text-gray-900 font-medium text-lg mb-4 leading-relaxed">
            {question.question_text}
          </p>
          
          {question.tags && (
            <div className="flex flex-wrap gap-2 mb-4">
              <Tag className="w-4 h-4 text-gray-400" />
              {question.tags.split(',').map((tag, tagIndex) => (
                <span
                  key={tagIndex}
                  className="px-2 py-1 bg-gray-50 text-gray-600 rounded-lg text-xs border border-gray-200"
                >
                  {tag.trim()}
                </span>
              ))}
            </div>
          )}
          
          <div className="flex items-center text-xs text-gray-500">
            <Calendar className="w-3 h-3 mr-1" />
            Created: {new Date(question.created_at).toLocaleDateString()}
          </div>
        </div>

        <div className="flex flex-col space-y-3 ml-6">
          {/* Difficulty Selector */}
          <select
            value={question.difficulty}
            onChange={(e) => onUpdateDifficulty(question.id, parseInt(e.target.value))}
            className="text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white hover:border-gray-400 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all duration-200"
          >
            {[1, 2, 3, 4, 5].map(level => (
              <option key={level} value={level}>Level {level}</option>
            ))}
          </select>

          <div className="flex space-x-2">
            <motion.button
              onClick={() => onToggleFlag(question.id)}
              className={`p-2 rounded-lg transition-all duration-200 ${
                question.is_flagged
                  ? 'bg-warning-100 text-warning-600 border border-warning-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-warning-100 hover:text-warning-600 border border-gray-200'
              }`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Flag className="w-4 h-4" />
            </motion.button>

            <motion.button
              onClick={() => onDelete(question.id)}
              className="p-2 bg-gray-100 text-gray-600 hover:bg-error-100 hover:text-error-600 rounded-lg transition-all duration-200 border border-gray-200"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Trash2 className="w-4 h-4" />
            </motion.button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default QuestionCard;