import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search, Filter, MessageSquare, SlidersHorizontal, ChevronDown } from 'lucide-react';
import { questionsApi, parseAxiosError } from '../services/api';
import { Question } from '../types';
import { ErrorResponse } from '../services/errorHandler';
import QuestionCard from '../components/QuestionCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Alert from '../components/Alert';
import EmptyState from '../components/EmptyState';
import toast from 'react-hot-toast';

const Questions: React.FC = () => {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [filteredQuestions, setFilteredQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ErrorResponse | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [selectedJobTitle, setSelectedJobTitle] = useState('all');
  const [jobTitles, setJobTitles] = useState<string[]>([]);
  const [operationLoading, setOperationLoading] = useState<number | null>(null);

  useEffect(() => {
    fetchQuestions();
    fetchJobTitles();
  }, []);

  useEffect(() => {
    const filtered = questions.filter((q) => {
      const matchesSearch =
        q.question_text.toLowerCase().includes(searchTerm.toLowerCase()) ||
        q.job_title.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = selectedType === 'all' || q.question_type === selectedType;
      const matchesJob = selectedJobTitle === 'all' || q.job_title === selectedJobTitle;
      return matchesSearch && matchesType && matchesJob;
    });
    setFilteredQuestions(filtered);
  }, [questions, searchTerm, selectedType, selectedJobTitle]);

  const fetchQuestions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await questionsApi.getAll({ limit: 1000 });
      setQuestions(response.data);
    } catch (err) {
      setError(parseAxiosError(err));
    } finally {
      setLoading(false);
    }
  };

  const fetchJobTitles = async () => {
    try {
      const response = await questionsApi.getJobTitles();
      setJobTitles(response.data);
    } catch {
      // non-critical
    }
  };

  const toggleFlag = async (questionId: number) => {
    try {
      setOperationLoading(questionId);
      const question = questions.find((q) => q.id === questionId);
      if (!question) return;
      await questionsApi.update(questionId, { is_flagged: !question.is_flagged });
      setQuestions((prev) =>
        prev.map((q) => (q.id === questionId ? { ...q, is_flagged: !q.is_flagged } : q))
      );
      toast.success(question.is_flagged ? 'Unflagged' : 'Flagged');
    } catch {
      toast.error('Failed to update question');
    } finally {
      setOperationLoading(null);
    }
  };

  const updateDifficulty = async (questionId: number, newDifficulty: number) => {
    try {
      setOperationLoading(questionId);
      await questionsApi.update(questionId, { difficulty: newDifficulty });
      setQuestions((prev) =>
        prev.map((q) => (q.id === questionId ? { ...q, difficulty: newDifficulty } : q))
      );
      toast.success('Difficulty updated');
    } catch {
      toast.error('Failed to update difficulty');
    } finally {
      setOperationLoading(null);
    }
  };

  const deleteQuestion = async (questionId: number) => {
    if (!window.confirm('Delete this question?')) return;
    try {
      setOperationLoading(questionId);
      await questionsApi.delete(questionId);
      setQuestions((prev) => prev.filter((q) => q.id !== questionId));
      toast.success('Question deleted');
    } catch {
      toast.error('Failed to delete question');
    } finally {
      setOperationLoading(null);
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
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 bg-blue-500/15 rounded-lg flex items-center justify-center">
            <MessageSquare className="w-4 h-4 text-blue-400" />
          </div>
          <h1 className="text-xl font-bold text-sidebar-text">Question Library</h1>
        </div>
        <p className="text-sm text-sidebar-muted">Browse, filter, and manage your interview questions.</p>
      </motion.div>

      {error && (
        <Alert
          type="error"
          title="Failed to load questions"
          message={error.message}
          actionLabel="Retry"
          onAction={fetchQuestions}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="bg-canvas-surface border border-canvas-border rounded-xl p-4"
      >
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Search */}
          <div className="relative sm:col-span-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sidebar-muted" />
            <input
              type="text"
              placeholder="Search questions…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-canvas-bg border border-canvas-border rounded-xl text-sm text-sidebar-text placeholder-sidebar-muted focus:outline-none focus:border-accent transition-colors"
            />
          </div>

          {/* Type filter */}
          <div className="relative">
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full px-4 py-2.5 bg-canvas-bg border border-canvas-border rounded-xl text-sm text-sidebar-text focus:outline-none focus:border-accent transition-colors appearance-none cursor-pointer"
            >
              <option value="all">All Types</option>
              <option value="technical">Technical</option>
              <option value="behavioral">Behavioral</option>
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sidebar-muted pointer-events-none" />
          </div>

          {/* Job title filter */}
          <div className="relative">
            <select
              value={selectedJobTitle}
              onChange={(e) => setSelectedJobTitle(e.target.value)}
              className="w-full px-4 py-2.5 bg-canvas-bg border border-canvas-border rounded-xl text-sm text-sidebar-text focus:outline-none focus:border-accent transition-colors appearance-none cursor-pointer"
            >
              <option value="all">All Roles</option>
              {jobTitles.map((title) => (
                <option key={title} value={title}>{title}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sidebar-muted pointer-events-none" />
          </div>
        </div>

        {/* Results count */}
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-canvas-border">
          <Filter className="w-3.5 h-3.5 text-sidebar-muted" />
          <span className="text-xs text-sidebar-muted">
            Showing <span className="text-sidebar-text font-medium">{filteredQuestions.length}</span> of{' '}
            <span className="text-sidebar-text font-medium">{questions.length}</span> questions
          </span>
        </div>
      </motion.div>

      {/* Questions list */}
      <div className="space-y-3">
        {filteredQuestions.length === 0 && questions.length > 0 ? (
          <EmptyState
            title="No questions match your filters"
            message={`Try adjusting your search or filters. ${questions.length} questions available.`}
            icon={<MessageSquare className="w-10 h-10 text-sidebar-muted" />}
            actionLabel="Clear Filters"
            onAction={() => { setSearchTerm(''); setSelectedType('all'); setSelectedJobTitle('all'); }}
          />
        ) : questions.length === 0 ? (
          <EmptyState
            title="No questions yet"
            message="Generate your first set of interview questions to get started."
            icon={<MessageSquare className="w-10 h-10 text-sidebar-muted" />}
            actionLabel="Generate Questions"
            onAction={() => (window.location.href = '/generate')}
          />
        ) : (
          filteredQuestions.map((question, index) => (
            <QuestionCard
              key={question.id}
              question={question}
              isLoading={operationLoading === question.id}
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
