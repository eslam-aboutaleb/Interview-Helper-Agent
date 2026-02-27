import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  Brain,
  CheckCircle2,
  ChevronDown,
  Zap,
  Clock,
  BarChart2,
  Tag,
} from 'lucide-react';
import { questionsApi, parseAxiosError } from '../services/api';
import { Question, QuestionGenerateRequest } from '../types';
import { ErrorResponse } from '../services/errorHandler';
import QuestionCard from '../components/QuestionCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Alert from '../components/Alert';
import toast from 'react-hot-toast';

// ─── AI Thinking Indicator ────────────────────────────────────────────────────

const thinkingSteps = [
  'Analyzing job requirements…',
  'Crafting technical questions…',
  'Adding behavioral questions…',
  'Calibrating difficulty levels…',
  'Tagging and categorizing…',
  'Finalizing your question set…',
];

const AIThinkingState: React.FC<{ jobTitle: string; count: number }> = ({ jobTitle, count }) => {
  const [stepIndex, setStepIndex] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const stepTimer = setInterval(() => {
      setStepIndex((i) => (i + 1) % thinkingSteps.length);
    }, 3500);
    const elapsedTimer = setInterval(() => {
      setElapsed((s) => s + 1);
    }, 1000);
    return () => {
      clearInterval(stepTimer);
      clearInterval(elapsedTimer);
    };
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="bg-canvas-surface border border-accent/20 rounded-xl p-6"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="relative">
          <div className="w-10 h-10 bg-accent/15 rounded-xl flex items-center justify-center">
            <Brain className="w-5 h-5 text-accent" />
          </div>
          {/* Pulse ring */}
          <span className="absolute inset-0 rounded-xl animate-ping bg-accent/20" />
        </div>
        <div>
          <p className="text-sm font-semibold text-sidebar-text">
            Generating {count} questions for <span className="text-accent">{jobTitle}</span>
          </p>
          <div className="flex items-center gap-1.5 mt-0.5">
            <Clock className="w-3.5 h-3.5 text-sidebar-muted" />
            <span className="text-xs text-sidebar-muted">{elapsed}s elapsed · This may take up to 60s</span>
          </div>
        </div>
      </div>

      {/* Animated step */}
      <div className="bg-canvas-bg rounded-lg px-4 py-3 mb-4 min-h-[40px] flex items-center">
        <AnimatePresence mode="wait">
          <motion.p
            key={stepIndex}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.3 }}
            className="text-sm text-accent font-medium"
          >
            {thinkingSteps[stepIndex]}
          </motion.p>
        </AnimatePresence>
      </div>

      {/* Progress dots */}
      <div className="flex items-center gap-1.5">
        {thinkingSteps.map((_, i) => (
          <motion.div
            key={i}
            className={`h-1.5 rounded-full transition-all duration-500 ${
              i === stepIndex ? 'w-6 bg-accent' : 'w-1.5 bg-canvas-hover'
            }`}
          />
        ))}
      </div>
    </motion.div>
  );
};

// ─── Results Summary Card ─────────────────────────────────────────────────────

const ResultsSummary: React.FC<{ questions: Question[] }> = ({ questions }) => {
  const technical = questions.filter((q) => q.question_type === 'technical').length;
  const behavioral = questions.filter((q) => q.question_type === 'behavioral').length;
  const avgDifficulty =
    questions.length > 0
      ? (questions.reduce((sum, q) => sum + q.difficulty, 0) / questions.length).toFixed(1)
      : '0';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-accent/10 border border-accent/20 rounded-xl p-4"
    >
      <div className="flex items-center gap-2 mb-3">
        <CheckCircle2 className="w-4 h-4 text-accent" />
        <span className="text-sm font-semibold text-accent">
          {questions.length} questions generated successfully
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="text-center">
          <p className="text-xl font-bold text-sidebar-text">{technical}</p>
          <p className="text-xs text-sidebar-muted">Technical</p>
        </div>
        <div className="text-center border-x border-accent/20">
          <p className="text-xl font-bold text-sidebar-text">{behavioral}</p>
          <p className="text-xs text-sidebar-muted">Behavioral</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-sidebar-text">{avgDifficulty}/5</p>
          <p className="text-xs text-sidebar-muted">Avg Difficulty</p>
        </div>
      </div>
    </motion.div>
  );
};

// ─── Main Component ───────────────────────────────────────────────────────────

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
  const resultsRef = useRef<HTMLDivElement>(null);

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
        toast.success(`${response.data.length} questions generated!`);
        // Scroll to results
        setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 200);
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
      toast.success(question.is_flagged ? 'Unflagged' : 'Flagged for review');
    } catch {
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
    } catch {
      toast.error('Failed to update difficulty');
    }
  };

  const deleteQuestion = async (questionId: number) => {
    if (!window.confirm('Delete this question? This cannot be undone.')) return;
    try {
      await questionsApi.delete(questionId);
      setGeneratedQuestions((prev) => prev.filter((q) => q.id !== questionId));
      toast.success('Question deleted');
    } catch {
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
          Use Google Gemini AI to create personalized interview questions tailored to your target role.
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
                disabled={loading}
                className={`w-full px-4 py-2.5 bg-canvas-bg border rounded-xl text-sm text-sidebar-text placeholder-sidebar-muted focus:outline-none focus:border-accent transition-colors disabled:opacity-50 ${
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
                  disabled={loading}
                  className="w-full px-4 py-2.5 bg-canvas-bg border border-canvas-border rounded-xl text-sm text-sidebar-text focus:outline-none focus:border-accent transition-colors appearance-none cursor-pointer disabled:opacity-50"
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
                  disabled={loading}
                  onClick={() => setFormData((p) => ({ ...p, question_type: opt.value as any }))}
                  className={`p-4 rounded-xl border text-left transition-colors duration-150 disabled:opacity-50 ${
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
                <span>AI is generating…</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                <span>Generate with AI</span>
              </>
            )}
          </motion.button>
        </form>
      </motion.div>

      {/* AI Thinking State */}
      <AnimatePresence>
        {loading && (
          <AIThinkingState jobTitle={formData.job_title} count={formData.count} />
        )}
      </AnimatePresence>

      {/* Results */}
      <AnimatePresence>
        {generatedQuestions.length > 0 && !loading && (
          <motion.div
            ref={resultsRef}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="space-y-4"
          >
            {/* Summary */}
            <ResultsSummary questions={generatedQuestions} />

            {/* Section header */}
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-sidebar-muted uppercase tracking-wider">
                Generated Questions
              </h2>
              <span className="text-xs text-sidebar-muted">
                Saved to your library automatically
              </span>
            </div>

            {/* Question cards */}
            <div className="space-y-3">
              {generatedQuestions.map((question, index) => (
                <QuestionCard
                  key={question.id}
                  question={question}
                  questionNumber={index + 1}
                  onToggleFlag={toggleFlag}
                  onUpdateDifficulty={updateDifficulty}
                  onDelete={deleteQuestion}
                  index={index}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Generate;
