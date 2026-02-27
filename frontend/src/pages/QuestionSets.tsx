import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FolderOpen, Plus } from 'lucide-react';
import { fetchQuestionSets, parseAxiosError } from '../services/api';
import { ErrorResponse } from '../services/errorHandler';
import QuestionSetCard from '../components/QuestionSetCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Alert from '../components/Alert';
import EmptyState from '../components/EmptyState';
import { QuestionSet } from '../types';

const QuestionSets: React.FC = () => {
  const [questionSets, setQuestionSets] = useState<QuestionSet[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<ErrorResponse | null>(null);

  useEffect(() => {
    loadQuestionSets();
  }, []);

  const loadQuestionSets = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchQuestionSets();
      setQuestionSets(data);
    } catch (err) {
      setError(parseAxiosError(err));
    } finally {
      setLoading(false);
    }
  };

  const getQuestionCount = (questionIds: string): number => {
    try {
      if (questionIds.startsWith('[')) return JSON.parse(questionIds).length;
      return questionIds.split(',').filter((id) => id.trim() !== '').length;
    } catch {
      return 0;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex items-start justify-between"
      >
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-8 h-8 bg-accent/15 rounded-lg flex items-center justify-center">
              <FolderOpen className="w-4 h-4 text-accent" />
            </div>
            <h1 className="text-xl font-bold text-sidebar-text">Question Sets</h1>
          </div>
          <p className="text-sm text-sidebar-muted">
            Organized collections of questions for focused practice sessions.
          </p>
        </div>

        <motion.button
          onClick={() => (window.location.href = '/questions')}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-xl text-sm font-medium transition-colors flex-shrink-0"
        >
          <Plus className="w-4 h-4" />
          Create Set
        </motion.button>
      </motion.div>

      {error && (
        <Alert
          type="error"
          title="Failed to load question sets"
          message={error.message}
          actionLabel="Retry"
          onAction={loadQuestionSets}
          onDismiss={() => setError(null)}
        />
      )}

      {questionSets.length === 0 ? (
        <EmptyState
          title="No question sets yet"
          message="Create your first question set to organize and practice specific interview topics."
          icon={<FolderOpen className="w-10 h-10 text-sidebar-muted" />}
          actionLabel="Go to Questions"
          onAction={() => (window.location.href = '/questions')}
        />
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {questionSets.map((set, index) => (
            <motion.div
              key={set.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              <QuestionSetCard
                id={set.id}
                name={set.name}
                description={set.description || ''}
                jobTitle={set.job_title}
                questionCount={getQuestionCount(set.question_ids)}
                onSelect={() => console.log(`Selected set ${set.id}`)}
              />
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
};

export default QuestionSets;
