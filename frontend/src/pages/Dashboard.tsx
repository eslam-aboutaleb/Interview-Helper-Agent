import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  MessageSquare,
  Sparkles,
  BarChart3,
  TrendingUp,
  Users,
  Flag,
  ArrowRight,
  FolderOpen,
} from 'lucide-react';
import { questionsApi, statsApi, parseAxiosError } from '../services/api';
import { Question, Stats } from '../types';
import { ErrorResponse } from '../services/errorHandler';
import StatCard from '../components/StatCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Alert from '../components/Alert';

const difficultyLabel = ['', 'Beginner', 'Easy', 'Medium', 'Hard', 'Expert'];

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentQuestions, setRecentQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ErrorResponse | null>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsRes, questionsRes] = await Promise.all([
        statsApi.get(),
        questionsApi.getAll({ limit: 5 }),
      ]);
      setStats(statsRes.data);
      setRecentQuestions(questionsRes.data);
    } catch (err) {
      setError(parseAxiosError(err));
    } finally {
      setLoading(false);
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
    <div className="space-y-8">
      {error && (
        <Alert
          type="error"
          title="Failed to load dashboard"
          message={error.message}
          actionLabel="Retry"
          onAction={fetchDashboardData}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="pt-2"
      >
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 bg-accent rounded-xl flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-sidebar-text">InterviewCoach</h1>
        </div>
        <p className="text-sidebar-muted text-sm leading-relaxed max-w-xl">
          AI-powered interview preparation. Generate personalized questions, track your progress,
          and ace your next interview.
        </p>
      </motion.div>

      {/* Quick actions */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="grid grid-cols-1 sm:grid-cols-3 gap-3"
      >
        {[
          {
            to: '/generate',
            label: 'Generate Questions',
            desc: 'Create AI-powered questions',
            icon: Sparkles,
            accent: true,
          },
          {
            to: '/questions',
            label: 'Question Library',
            desc: 'Browse & manage questions',
            icon: MessageSquare,
            accent: false,
          },
          {
            to: '/question-sets',
            label: 'Question Sets',
            desc: 'Organized collections',
            icon: FolderOpen,
            accent: false,
          },
        ].map((item, i) => (
          <motion.div
            key={item.to}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 + i * 0.07 }}
          >
            <Link
              to={item.to}
              className={`flex items-center justify-between p-4 rounded-xl border transition-colors duration-200 group ${
                item.accent
                  ? 'bg-accent/10 border-accent/30 hover:bg-accent/15'
                  : 'bg-canvas-surface border-canvas-border hover:border-canvas-hover'
              }`}
            >
              <div className="flex items-center gap-3">
                <item.icon
                  className={`w-5 h-5 ${item.accent ? 'text-accent' : 'text-sidebar-muted group-hover:text-sidebar-text'}`}
                />
                <div>
                  <p className={`text-sm font-medium ${item.accent ? 'text-accent' : 'text-sidebar-text'}`}>
                    {item.label}
                  </p>
                  <p className="text-xs text-sidebar-muted">{item.desc}</p>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-sidebar-muted group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </motion.div>
        ))}
      </motion.div>

      {/* Stats */}
      {stats && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
        >
          <h2 className="text-sm font-semibold text-sidebar-muted uppercase tracking-wider mb-3">
            Overview
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard title="Total Questions" value={stats.total_questions} subtitle="Generated" icon={MessageSquare} color="blue" index={0} />
            <StatCard title="Avg Difficulty" value={stats.average_difficulty.toFixed(1)} subtitle="Out of 5.0" icon={TrendingUp} color="green" index={1} />
            <StatCard title="Flagged" value={stats.flagged_questions} subtitle="Need review" icon={Flag} color="orange" index={2} />
            <StatCard title="Question Sets" value={stats.total_question_sets} subtitle="Collections" icon={Users} color="gray" index={3} />
          </div>
        </motion.div>
      )}

      {/* Recent questions */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-sidebar-muted uppercase tracking-wider">
            Recent Questions
          </h2>
          <Link
            to="/questions"
            className="text-xs text-accent hover:text-accent-hover transition-colors flex items-center gap-1"
          >
            View all <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {recentQuestions.length === 0 ? (
          <div className="bg-canvas-surface border border-canvas-border rounded-xl p-8 text-center">
            <MessageSquare className="w-8 h-8 text-sidebar-muted mx-auto mb-3" />
            <p className="text-sm font-medium text-sidebar-text mb-1">No questions yet</p>
            <p className="text-xs text-sidebar-muted mb-4">
              Generate your first set of interview questions to get started
            </p>
            <Link
              to="/generate"
              className="inline-flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Sparkles className="w-4 h-4" />
              Generate Questions
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {recentQuestions.map((q, i) => (
              <motion.div
                key={q.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, delay: i * 0.06 }}
                className="bg-canvas-surface border border-canvas-border rounded-xl p-4 hover:border-canvas-hover transition-colors"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium border ${
                          q.question_type === 'technical'
                            ? 'text-blue-400 bg-blue-400/10 border-blue-400/20'
                            : 'text-purple-400 bg-purple-400/10 border-purple-400/20'
                        }`}
                      >
                        {q.question_type}
                      </span>
                      <span className="text-xs text-sidebar-muted bg-canvas-hover px-2 py-0.5 rounded-full border border-canvas-border">
                        {difficultyLabel[q.difficulty] || `Level ${q.difficulty}`}
                      </span>
                      <span className="text-xs text-sidebar-muted">{q.job_title}</span>
                    </div>
                    <p className="text-sm text-sidebar-text leading-relaxed line-clamp-2">
                      {q.question_text}
                    </p>
                  </div>
                  {q.is_flagged && <Flag className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default Dashboard;
