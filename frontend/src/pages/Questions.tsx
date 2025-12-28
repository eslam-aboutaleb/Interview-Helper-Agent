import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search, Filter, MessageSquare, SlidersHorizontal, RefreshCw } from 'lucide-react';
import { questionsApi, parseAxiosError } from '../services/api';
import { Question } from '../types';
import { ErrorResponse, ErrorType } from '../services/errorHandler';
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
  const [showFilters, setShowFilters] = useState(false);
  const [operationLoading, setOperationLoading] = useState<number | null>(null);

  useEffect(() => {
    fetchQuestions();
    fetchJobTitles();
  }, []);

  useEffect(() => {
    filterQuestions();
  }, [questions, searchTerm, selectedType, selectedJobTitle]);

  const fetchQuestions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await questionsApi.getAll({ limit: 1000 });
      setQuestions(response.data);
      if (response.data.length === 0) {
        toast.info('No questions available');
      }
    } catch (err) {
      const parsedError = parseAxiosError(err);
      setError(parsedError);
      console.error('Failed to fetch questions:', parsedError);
    } finally {
      setLoading(false);
    }
  };

  const fetchJobTitles = async () => {
    try {
      const response = await questionsApi.getJobTitles();
      setJobTitles(response.data);
    } catch (err) {
      const parsedError = parseAxiosError(err);
      console.error('Failed to fetch job titles:', parsedError);
      toast.error('Failed to load job titles filter');
    }
  };

  const filterQuestions = () => {
    let filtered = questions.filter(question => {
      const matchesSearch = question.question_text.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           question.job_title.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = selectedType === 'all' || question.question_type === selectedType;
      const matchesJob = selectedJobTitle === 'all' || question.job_title === selectedJobTitle;
      
      return matchesSearch && matchesType && matchesJob;
    });
    setFilteredQuestions(filtered);
  };

  const toggleFlag = async (questionId: number) => {
    try {
      setOperationLoading(questionId);
      const question = questions.find(q => q.id === questionId);
      if (!question) {
        toast.error('Question not found');
        return;
      }

      await questionsApi.update(questionId, {
        is_flagged: !question.is_flagged
      });
      
      setQuestions(prev => 
        prev.map(q => 
          q.id === questionId 
            ? { ...q, is_flagged: !q.is_flagged }
            : q
        )
      );
      
      toast.success(question.is_flagged ? 'Question unflagged' : 'Question flagged');
    } catch (err) {
      const parsedError = parseAxiosError(err);
      toast.error(`Failed to update question: ${parsedError.message}`);
      console.error('Failed to toggle flag:', parsedError);
    } finally {
      setOperationLoading(null);
    }
  };

  const updateDifficulty = async (questionId: number, newDifficulty: number) => {
    try {
      setOperationLoading(questionId);
      await questionsApi.update(questionId, {
        difficulty: newDifficulty
      });
      
      setQuestions(prev => 
        prev.map(q => 
          q.id === questionId 
            ? { ...q, difficulty: newDifficulty }
            : q
        )
      );
      
      toast.success('Difficulty updated successfully');
    } catch (err) {
      const parsedError = parseAxiosError(err);
      toast.error(`Failed to update difficulty: ${parsedError.message}`);
      console.error('Failed to update difficulty:', parsedError);
    } finally {
      setOperationLoading(null);
    }
  };

  const deleteQuestion = async (questionId: number) => {
    if (!window.confirm('Are you sure you want to delete this question? This action cannot be undone.')) {
      return;
    }
    
    try {
      setOperationLoading(questionId);
      await questionsApi.delete(questionId);
      setQuestions(prev => prev.filter(q => q.id !== questionId));
      toast.success('Question deleted successfully');
    } catch (err) {
      const parsedError = parseAxiosError(err);
      toast.error(`Failed to delete question: ${parsedError.message}`);
      console.error('Failed to delete question:', parsedError);
    } finally {
      setOperationLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Error Alert */}
      {error && (
        <Alert
          type="error"
          title="Failed to Load Questions"
          message={error.message}
          details={error.details}
          actionLabel="Retry"
          onAction={fetchQuestions}
          onDismiss={() => setError(null)}
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
        className={`bg-white rounded-2xl border border-gray-200 p-6 shadow-soft ${showFilters ? 'block' : 'hidden md:block'}`}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
      >
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" aria-hidden="true" />
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
            {jobTitles.map(title => (
              <option key={title} value={title}>{title}</option>
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
            onAction={() => window.location.href = '/generate'}
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