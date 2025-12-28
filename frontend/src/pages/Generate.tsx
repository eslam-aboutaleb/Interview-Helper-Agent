import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Brain, Wand2, CheckCircle, AlertCircle } from 'lucide-react';
import { questionsApi, parseAxiosError } from '../services/api';
import { Question, QuestionGenerateRequest } from '../types';
import { ErrorResponse, ErrorType } from '../services/errorHandler';
import QuestionCard from '../components/QuestionCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Alert from '../components/Alert';
import EmptyState from '../components/EmptyState';
import toast from 'react-hot-toast';

const Generate: React.FC = () => {
  const [formData, setFormData] = useState<QuestionGenerateRequest>({
    job_title: '',
    count: 5,
    question_type: 'mixed'
  });
  const [loading, setLoading] = useState(false);
  const [generatedQuestions, setGeneratedQuestions] = useState<Question[]>([]);
  const [error, setError] = useState<ErrorResponse | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};
    
    if (!formData.job_title.trim()) {
      errors.job_title = 'Job title is required';
    } else if (formData.job_title.length < 2) {
      errors.job_title = 'Job title must be at least 2 characters';
    } else if (formData.job_title.length > 100) {
      errors.job_title = 'Job title cannot exceed 100 characters';
    }
    
    if (formData.count < 1 || formData.count > 100) {
      errors.count = 'Number of questions must be between 1 and 100';
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      toast.error('Please fix the validation errors');
      return;
    }
    
    setLoading(true);
    setError(null);
    setGeneratedQuestions([]);
    
    try {
      const response = await questionsApi.generate(formData);
      setGeneratedQuestions(response.data);
      if (response.data.length === 0) {
        toast.warning('No questions were generated. Please try again.');
      } else {
        toast.success(`Generated ${response.data.length} questions successfully!`);
      }
    } catch (err) {
      const parsedError = parseAxiosError(err);
      setError(parsedError);
      console.error('Generation failed:', parsedError);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'count' ? parseInt(value) : value
    }));
    // Clear validation error for this field
    setValidationErrors(prev => ({
      ...prev,
      [name]: ''
    }));
  };

  const handleQuestionTypeChange = (type: 'mixed' | 'technical' | 'behavioral') => {
    setFormData(prev => ({ ...prev, question_type: type }));
  };

  const toggleFlag = async (questionId: number) => {
    try {
      const question = generatedQuestions.find(q => q.id === questionId);
      if (!question) {
        toast.error('Question not found');
        return;
      }

      await questionsApi.update(questionId, {
        is_flagged: !question.is_flagged
      });
      
      setGeneratedQuestions(prev => 
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
    }
  };

  const updateDifficulty = async (questionId: number, newDifficulty: number) => {
    try {
      await questionsApi.update(questionId, {
        difficulty: newDifficulty
      });
      
      setGeneratedQuestions(prev => 
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
    }
  };

  const deleteQuestion = async (questionId: number) => {
    if (!window.confirm('Are you sure you want to delete this question? This action cannot be undone.')) {
      return;
    }
    
    try {
      await questionsApi.delete(questionId);
      setGeneratedQuestions(prev => prev.filter(q => q.id !== questionId));
      toast.success('Question deleted successfully');
    } catch (err) {
      const parsedError = parseAxiosError(err);
      toast.error(`Failed to delete question: ${parsedError.message}`);
      console.error('Failed to delete question:', parsedError);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Error Alert */}
      {error && (
        <Alert
          type="error"
          title="Generation Failed"
          message={error.message}
          details={error.details}
          actionLabel="Try Again"
          onAction={() => {
            setError(null);
            setGeneratedQuestions([]);
          }}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Header */}
      <motion.div 
        className="text-center"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="inline-flex items-center space-x-3 mb-6">
          <motion.div 
            className="p-4 bg-gradient-to-br from-gray-700 to-gray-800 rounded-2xl shadow-strong"
            whileHover={{ scale: 1.05, rotate: 5 }}
          >
            <Wand2 className="w-8 h-8 text-white" />
          </motion.div>
          <h1 className="text-4xl font-bold text-gray-900">Generate Questions</h1>
        </div>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          Use advanced AI to create personalized interview questions tailored to your target role and experience level
        </p>
      </motion.div>

      {/* Generation Form */}
      <motion.div 
        className="bg-white rounded-2xl border border-gray-200 p-8 shadow-soft"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        <form onSubmit={handleSubmit} className="space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                Job Title *
              </label>
              <input
                type="text"
                name="job_title"
                value={formData.job_title}
                onChange={handleInputChange}
                placeholder="e.g., Software Engineer, Data Scientist, Product Manager"
                aria-label="Job title for generating questions"
                className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:border-blue-500 transition-all duration-200 bg-gray-50 focus:bg-white ${
                  validationErrors.job_title 
                    ? 'border-error-300 focus:ring-error-500' 
                    : 'border-gray-300 focus:ring-blue-500'
                }`}
              />
              {validationErrors.job_title && (
                <p className="text-error-600 text-sm mt-2">{validationErrors.job_title}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                Number of Questions
              </label>
              <select
                name="count"
                value={formData.count}
                onChange={handleInputChange}
                aria-label="Number of questions to generate"
                className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:border-blue-500 transition-all duration-200 bg-gray-50 focus:bg-white ${
                  validationErrors.count 
                    ? 'border-error-300 focus:ring-error-500' 
                    : 'border-gray-300 focus:ring-blue-500'
                }`}
              >
                <option value={3}>3 Questions</option>
                <option value={5}>5 Questions</option>
                <option value={10}>10 Questions</option>
                <option value={15}>15 Questions</option>
              </select>
              {validationErrors.count && (
                <p className="text-error-600 text-sm mt-2">{validationErrors.count}</p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-4">
              Question Type
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { 
                  value: 'mixed', 
                  label: 'Mixed Questions', 
                  description: 'Technical & Behavioral',
                  icon: '🎯'
                },
                { 
                  value: 'technical', 
                  label: 'Technical Only', 
                  description: 'Skills & Knowledge',
                  icon: '💻'
                },
                { 
                  value: 'behavioral', 
                  label: 'Behavioral Only', 
                  description: 'Soft Skills & Experience',
                  icon: '🤝'
                }
              ].map((option) => (
                <motion.label
                  key={option.value}
                  className={`relative p-6 border-2 rounded-xl cursor-pointer transition-all duration-200 ${
                    formData.question_type === option.value
                      ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-slate-50 shadow-medium'
                      : 'border-gray-200 hover:border-gray-300 hover:shadow-soft'
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <input
                    type="radio"
                    name="question_type"
                    value={option.value}
                    checked={formData.question_type === option.value}
                    onChange={() => handleQuestionTypeChange(option.value as any)}
                    className="sr-only"
                  />
                  <div className="text-center">
                    <div className="text-2xl mb-2">{option.icon}</div>
                    <div className="text-sm font-semibold text-gray-900 mb-1">{option.label}</div>
                    <div className="text-xs text-gray-600">{option.description}</div>
                  </div>
                  {formData.question_type === option.value && (
                    <motion.div
                      className="absolute top-2 right-2"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                    >
                      <CheckCircle className="w-5 h-5 text-gray-700" />
                    </motion.div>
                  )}
                </motion.label>
              ))}
            </div>
          </div>

          {error && (
            <motion.div 
              className="p-4 bg-error-50 border border-error-200 rounded-xl flex items-center space-x-3"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <AlertCircle className="w-5 h-5 text-error-600" />
              <p className="text-error-700 font-medium">{error}</p>
            </motion.div>
          )}

          <motion.button
            type="submit"
            disabled={loading || !formData.job_title}
            className="w-full flex items-center justify-center space-x-3 px-8 py-4 bg-gradient-to-r from-gray-700 to-gray-800 text-white rounded-xl font-semibold shadow-strong hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
            whileHover={{ scale: loading ? 1 : 1.02 }}
            whileTap={{ scale: loading ? 1 : 0.98 }}
          >
            {loading ? (
              <>
                <LoadingSpinner size="sm" className="border-white border-t-transparent" />
                <span>Generating Questions...</span>
              </>
            ) : (
              <>
                <Brain className="w-5 h-5" />
                <span>Generate Questions with AI</span>
                <Sparkles className="w-4 h-4" />
              </>
            )}
          </motion.button>
        </form>
      </motion.div>

      {/* Generated Questions */}
      {generatedQuestions.length > 0 && (
        <motion.div 
          className="bg-white rounded-2xl border border-gray-200 p-8 shadow-soft"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="flex items-center space-x-3 mb-8">
            <CheckCircle className="w-6 h-6 text-success-600" />
            <h2 className="text-2xl font-bold text-gray-900">Generated Questions</h2>
            <span className="px-3 py-1 bg-success-100 text-success-800 rounded-full text-sm font-medium">
              {generatedQuestions.length} questions
            </span>
          </div>

          <div className="space-y-6">
            {generatedQuestions.map((question, index) => (
              <QuestionCard
                key={question.id}
                question={question}
                onToggleFlag={toggleFlag}
                onUpdateDifficulty={updateDifficulty}
                onDelete={deleteQuestion}
                index={index}
              />
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default Generate;