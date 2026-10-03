import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Filter, MessageSquare, SlidersHorizontal } from 'lucide-react';
import { questionsApi, parseAxiosError } from '../services/api';
import { Question, QuestionUpdateRequest } from '../types';
import { ErrorResponse } from '../services/errorHandler';
import QuestionCard from '../components/QuestionCard';
import Alert from '../components/Alert';
import EmptyState from '../components/EmptyState';
import { Skeleton } from '../components/ui/Skeleton';
import toast from 'react-hot-toast';

const Questions: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [selectedJobTitle, setSelectedJobTitle] = useState('all');
  const [showFilters, setShowFilters] = useState(false);
  const [pendingId, setPendingId] = useState<number | null>(null);

  const {
    data: questions = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<Question[]>({
    queryKey: ['questions', 'all'],
    queryFn: () => questionsApi.getAll({ limit: 1000 }).then((r) => r.data),
  });

  const { data: jobTitles = [] } = useQuery<string[]>({
    queryKey: ['job-titles'],
    queryFn: () => questionsApi.getJobTitles().then((r) => r.data),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: QuestionUpdateRequest }) =>
      questionsApi.update(id, data).then((r) => r.data),
    onMutate: ({ id }) => setPendingId(id),
    onSettled: () => setPendingId(null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
    onError: (err: unknown) => {
      const parsed = parseAxiosError(err);
      toast.error(`Failed to update question: ${parsed.message}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => questionsApi.delete(id).then(() => id),
    onMutate: (id) => setPendingId(id),
    onSettled: () => setPendingId(null),
    onSuccess: () => {
      toast.success('Question deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['questions'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
    onError: (err: unknown) => {
      const parsed = parseAxiosError(err);
      toast.error(`Failed to delete question: ${parsed.message}`);
    },
  });

  const filteredQuestions = useMemo(() => {
    return questions.filter((question) => {
      const matchesSearch =
        question.question_text.toLowerCase().includes(searchTerm.toLowerCase()) ||
        question.job_title.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = selectedType === 'all' || question.question_type === selectedType;
      const matchesJob = selectedJobTitle === 'all' || question.job_title === selectedJobTitle;
      return matchesSearch && matchesType && matchesJob;
    });
  }, [questions, searchTerm, selectedType, selectedJobTitle]);

  const toggleFlag = (questionId: number) => {
    const question = questions.find((q) => q.id === questionId);
    if (!question) {
      toast.error('Question not found');
      return;
    }
    updateMutation.mutate({
      id: questionId,
      data: { is_flagged: !question.is_flagged },
    });
  };

  const updateDifficulty = (questionId: number, newDifficulty: number) => {
    updateMutation.mutate({ id: questionId, data: { difficulty: newDifficulty } });
  };

  const deleteQuestion = (questionId: number) => {
    if (
      !window.confirm(
        'Are you sure you want to delete this question? This action cannot be undone.'
      )
    ) {
      return;
    }
    deleteMutation.mutate(questionId);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton width={240} height={36} />
            <Skeleton width={320} height={20} className="mt-2" />
          </div>
        </div>
        <Skeleton width="100%" height={72} variant="rectangular" />
        <div className="space-y-4">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} width="100%" height={140} variant="rectangular" />
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
          title="Failed to Load Questions"
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
          <h1 className="text-4xl font-bold text-gray-900">Question Library</h1>
          <p className="text-gray-600 mt-2">Manage and organize your interview questions</p>
        </div>

        <motion.button
          onClick={() => setShowFilters(!showFilters)}
          aria-label="Toggle filters"
          className="md:hidden flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors duration-200"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <SlidersHorizontal className="w-4 h-4" />
          <span>Filters</span>
        </motion.button>
      </motion.div>

      {/* Filters */}
      <motion.div
        className={`bg-white rounded-2xl border border-gray-200 p-6 shadow-soft ${
          showFilters ? 'block' : 'hidden md:block'
        }`}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
      >
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"
              aria-hidden="true"
            />
            <input
              type="text"
              placeholder="Search questions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              aria-label="Search questions"
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 bg-gray-50 focus:bg-white"
            />
          </div>

          {/* Type Filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            aria-label="Filter by question type"
            className="px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 bg-gray-50 focus:bg-white"
          >
            <option value="all">All Types</option>
            <option value="technical">Technical</option>
            <option value="behavioral">Behavioral</option>
          </select>

          {/* Job Title Filter */}
          <select
            value={selectedJobTitle}
            onChange={(e) => setSelectedJobTitle(e.target.value)}
            aria-label="Filter by job title"
            className="px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 bg-gray-50 focus:bg-white"
          >
            <option value="all">All Job Titles</option>
            {jobTitles.map((title) => (
              <option key={title} value={title}>
                {title}
              </option>
            ))}
          </select>

          {/* Results Count */}
          <div className="flex items-center justify-center md:justify-start text-sm text-gray-600 bg-gray-50 rounded-xl px-4 py-3 border border-gray-200">
            <Filter className="w-4 h-4 mr-2" aria-hidden="true" />
            <span className="font-medium">{filteredQuestions.length}</span>
            <span className="mx-1">of</span>
            <span className="font-medium">{questions.length}</span>
            <span className="ml-1">questions</span>
          </div>
        </div>
      </motion.div>

      {/* Questions List */}
      <div className="space-y-4">
        {filteredQuestions.length === 0 && questions.length > 0 ? (
          <EmptyState
            title="No questions match your filters"
            message={`Try adjusting your search or filters. There are ${questions.length} questions available in total.`}
            icon={<MessageSquare className="w-12 h-12 text-gray-400" />}
            actionLabel="Clear Filters"
            onAction={() => {
              setSearchTerm('');
              setSelectedType('all');
              setSelectedJobTitle('all');
            }}
          />
        ) : questions.length === 0 ? (
          <EmptyState
            title="No questions yet"
            message="Generate new questions to get started with your interview preparation."
            icon={<MessageSquare className="w-12 h-12 text-gray-400" />}
            actionLabel="Generate Questions"
            onAction={() => (window.location.href = '/generate')}
          />
        ) : (
          filteredQuestions.map((question, index) => (
            <QuestionCard
              key={question.id}
              question={question}
              isLoading={pendingId === question.id}
              onToggleFlag={toggleFlag}
              onUpdateDifficulty={updateDifficulty}
              onDelete={deleteQuestion}
              index={index}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default Questions;
