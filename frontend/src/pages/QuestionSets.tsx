import React from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { FolderOpen, Plus } from 'lucide-react';
import { questionSetsApi, parseAxiosError } from '../services/api';
import { ErrorResponse } from '../services/errorHandler';
import QuestionSetCard from '../components/QuestionSetCard';
import Alert from '../components/Alert';
import EmptyState from '../components/EmptyState';
import { Skeleton } from '../components/ui/Skeleton';
import { QuestionSet } from '../types';

const QuestionSets: React.FC = () => {
  const {
    data: questionSets = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<QuestionSet[]>({
    queryKey: ['question-sets'],
    queryFn: () => questionSetsApi.getAll().then((r) => r.data),
  });

  // Calculate question count from the question_ids field
  const getQuestionCount = (questionIds: string): number => {
    try {
      if (questionIds.startsWith('[')) {
        return JSON.parse(questionIds).length;
      }
      return questionIds.split(',').filter((id) => id.trim() !== '').length;
    } catch (e) {
      console.error('Error parsing question_ids:', e);
      return 0;
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton width={200} height={36} />
            <Skeleton width={320} height={20} className="mt-2" />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} width="100%" height={180} variant="rectangular" />
          ))}
        </div>
      </div>
    );
  }

  const queryError: ErrorResponse | null = isError ? parseAxiosError(error) : null;

  return (
    <div className="space-y-6">
      {queryError && (
        <Alert
          type="error"
          title="Failed to Load Question Sets"
          message={queryError.message}
          details={queryError.details}
          actionLabel="Retry"
          onAction={() => refetch()}
        />
      )}

      {/* Header */}
      <motion.div
        className="flex items-center justify-between"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div>
          <h1 className="text-4xl font-bold text-gray-900">Question Sets</h1>
          <p className="text-gray-600 mt-2">Create and organize themed question collections</p>
        </div>

        <motion.button
          onClick={() => (window.location.href = '/questions')}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors duration-200"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Plus className="w-4 h-4" />
          <span>Create Set</span>
        </motion.button>
      </motion.div>

      {questionSets.length === 0 ? (
        <EmptyState
          title="No question sets yet"
          message="Create your first question set to organize and practice specific interview topics."
          icon={<FolderOpen className="w-12 h-12 text-gray-400" />}
          actionLabel="Create Question Set"
          onAction={() => (window.location.href = '/questions')}
        />
      ) : (
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          {questionSets.map((set, index) => (
            <motion.div
              key={set.id}
              initial={{ opacity: 0, y: 20 }}
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
