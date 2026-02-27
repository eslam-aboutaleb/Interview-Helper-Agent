import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Brain, CheckCircle2, ChevronDown } from 'lucide-react';
import { questionsApi, parseAxiosError } from '../services/api';
import { Question, QuestionGenerateRequest } from '../types';
import { ErrorResponse } from '../services/errorHandler';
import QuestionCard from '../components/QuestionCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Alert from '../components/Alert';
import toast from 'react-hot-toast';

const Generate: React.FC = () => {
  const [formData, setFormData] = useState<QuestionGenerateRequest>({
    job_title: '',
    count: 5,
    question_type: 'mixed',
  });
  const [loading, setLoading] = useState(false);
  const [generatedQuestions, setGeneratedQuestions] = useState<Question[]>([]);
  const [error, setError] = useState<ErrorResponse | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};
    if (!formData.job_title.trim()) errors.job_title = 'Job title is required';
    else if (formData.job_title.length < 2) errors.job_title = 'At least 2 characters';
    else if (formData.job_title.length > 100) errors.job_title = 'Max 100 characters';
    if (formData.count < 1 || formData.count > 100) errors.count = 'Between 1 and 100';
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
    setLoading(true);
    setError(null);
    setGeneratedQuestions([]);
    try {
      const response = await questionsApi.generate(formData);
      setGeneratedQuestions(response.data);
      if (response.data.length === 0) {
        toast.error('No questions were generated. Please try again.');
      } else {
        toast.success(`Generated ${response.data.length} questions!`);
      }
    } catch (err) {
      setError(parseAxiosError(err));
    } finally {
      setLoading(false);
    }
  };

  const toggleFlag = async (questionId: number) => {
    try {
      const question = generatedQuestions.find((q) => q.id === questionId);
      if (!question) return;
      await questionsApi.update(questionId, { is_flagged: !question.is_flagged });
      setGeneratedQuestions((prev) =>
        prev.map((q) => (q.id === questionId ? { ...q, is_flagged: !q.is_flagged } : q))
      );
      toast.success(question.is_flagged ? 'Unflagged' : 'Flagged');
    } catch (err) {
      toast.error('Failed to update question');
    }
  };

  const updateDifficulty = async (questionId: number, newDifficulty: number) => {
    try {
      await questionsApi.update(questionId, { difficulty: newDifficulty });
      setGeneratedQuestions((prev) =>
        prev.map((q) => (q.id === questionId ? { ...q, difficulty: newDifficulty } : q))
      );
      toast.success('Difficulty updated');
    } catch (err) {
      toast.error('Failed to update difficulty');
    }
  };

  const deleteQuestion = async (questionId: number) => {
    if (!window.confirm('Delete this question?')) return;
    try {
      await questionsApi.delete(questionId);
      setGeneratedQuestions((prev) => prev.filter((q) => q.id !== questionId));
      toast.success('Question deleted');
    } catch (err) {
      toast.error('Failed to delete question');
    }
  };

  const questionTypes = [
    { value: 'mixed', label: 'Mixed', desc: 'Technical & Behavioral', emoji: '🎯' },
    { value: 'technical', label: 'Technical', desc: 'Skills & Knowledge', emoji: '💻' },
    { value: 'behavioral', label: 'Behavioral', desc: 'Soft Skills', emoji: '🤝' },
  ];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 bg-accent/15 rounded-lg flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-accent" />
          </div>
          <h1 className="text-xl font-bold text-sidebar-text">Generate Questions</h1>
        </div>
        <p className="text-sm text-sidebar-muted">
          Use AI to create personalized interview questions tailored to your target role.
        </p>
      </motion.div>

      {error && (
        <Alert
          type="error"
          title="Generation failed"
          message={error.message}
          actionLabel="Try again"
          onAction={() => { setError(null); setGeneratedQuestions([]); }}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Form */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="bg-canvas-surface border border-canvas-border rounded-xl p-6"
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Job title + count */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-sidebar-muted uppercase tracking-wider mb-2">
                Job Title *
              </label>
              <input
                type="text"
                value={formData.job_title}
                onChange={(e) => {
                  setFormData((p) => ({ ...p, job_title: e.target.value }));
                  setValidationErrors((p) => ({ ...p, job_title: '' }));
                }}
                placeholder="e.g. Software Engineer, Data Scientist"
                className={`w-full px-4 py-2.5 bg-canvas-bg border rounded-xl text-sm text-sidebar-text placeholder-sidebar-muted focus:outline-none focus:border-accent transition-colors ${
                  validationErrors.job_title ? 'border-red-500/50' : 'border-canvas-border'
                }`}
              />
              {validationErrors.job_title && (
                <p className="text-xs text-red-400 mt-1">{validationErrors.job_title}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-sidebar-muted uppercase tracking-wider mb-2">
                Number of Questions
              </label>
              <div className="relative">
                <select
                  value={formData.count}
                  onChange={(e) => setFormData((p) => ({ ...p, count: parseInt(e.target.value) }))}
                  className="w-full px-4 py-2.5 bg-canvas-bg border border-canvas-border rounded-xl text-sm text-sidebar-text focus:outline-none focus:border-accent transition-colors appearance-none cursor-pointer"
                >
                  {[3, 5, 10, 15, 20].map((n) => (
                    <option key={n} value={n}>{n} Questions</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sidebar-muted pointer-events-none" />
              </div>
            </div>
          </div>

          {/* Question type */}
          <div>
            <label className="block text-xs font-semibold text-sidebar-muted uppercase tracking-wider mb-3">
              Question Type
            </label>
            <div className="grid grid-cols-3 gap-3">
              {questionTypes.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setFormData((p) => ({ ...p, question_type: opt.value as any }))}
                  className={`p-4 rounded-xl border text-left transition-colors duration-150 ${
                    formData.question_type === opt.value
                      ? 'border-accent bg-accent/10'
                      : 'border-canvas-border bg-canvas-bg hover:border-canvas-hover'
                  }`}
                >
                  <div className="text-xl mb-2">{opt.emoji}</div>
                  <p className={`text-sm font-medium ${formData.question_type === opt.value ? 'text-accent' : 'text-sidebar-text'}`}>
                    {opt.label}
                  </p>
                  <p className="text-xs text-sidebar-muted mt-0.5">{opt.desc}</p>
                  {formData.question_type === opt.value && (
                    <CheckCircle2 className="w-4 h-4 text-accent mt-2" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Submit */}
          <motion.button
            type="submit"
            disabled={loading || !formData.job_title.trim()}
            whileHover={{ scale: loading ? 1 : 1.01 }}
            whileTap={{ scale: loading ? 1 : 0.99 }}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-accent hover:bg-accent-hover text-white rounded-xl font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <>
                <LoadingSpinner size="sm" className="border-white/30 border-t-white" />
                <span>Generating questions…</span>
              </>
            ) : (
              <>
                <Brain className="w-4 h-4" />
                <span>Generate with AI</span>
              </>
            )}
          </motion.button>
        </form>
      </motion.div>

      {/* Results */}
      {generatedQuestions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle2 className="w-5 h-5 text-accent" />
            <h2 className="text-base font-semibold text-sidebar-text">
              Generated Questions
            </h2>
            <span className="px-2.5 py-0.5 bg-accent/15 text-accent rounded-full text-xs font-medium">
              {generatedQuestions.length}
            </span>
          </div>

          <div className="space-y-3">
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
