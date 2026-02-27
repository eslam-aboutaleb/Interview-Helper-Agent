import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp, Users, MessageSquare, Flag, Target, Award } from 'lucide-react';
import { statsApi, parseAxiosError } from '../services/api';
import { Stats } from '../types';
import { ErrorResponse } from '../services/errorHandler';
import StatCard from '../components/StatCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Alert from '../components/Alert';
import EmptyState from '../components/EmptyState';

const StatsPage: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ErrorResponse | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await statsApi.get();
      setStats(response.data);
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

  if (error) {
    return (
      <Alert
        type="error"
        title="Failed to load statistics"
        message={error.message}
        actionLabel="Retry"
        onAction={fetchStats}
        onDismiss={() => setError(null)}
      />
    );
  }

  if (!stats) {
    return (
      <EmptyState
        title="No statistics available"
        message="Start generating and rating questions to see your statistics."
        icon={<BarChart3 className="w-10 h-10 text-sidebar-muted" />}
        actionLabel="Generate Questions"
        onAction={() => (window.location.href = '/generate')}
      />
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 bg-green-500/15 rounded-lg flex items-center justify-center">
            <BarChart3 className="w-4 h-4 text-green-400" />
          </div>
          <h1 className="text-xl font-bold text-sidebar-text">Statistics</h1>
        </div>
        <p className="text-sm text-sidebar-muted">
          Track your interview preparation progress and analyze question patterns.
        </p>
      </motion.div>

      {/* Overview cards */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-3"
      >
        <StatCard title="Total Questions" value={stats.total_questions} subtitle="Generated" icon={MessageSquare} color="blue" index={0} />
        <StatCard title="Avg Difficulty" value={stats.average_difficulty.toFixed(1)} subtitle="Out of 5.0" icon={TrendingUp} color="green" index={1} />
        <StatCard title="Flagged" value={stats.flagged_questions} subtitle="Need review" icon={Flag} color="orange" index={2} />
        <StatCard title="Question Sets" value={stats.total_question_sets} subtitle="Collections" icon={Users} color="gray" index={3} />
      </motion.div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By type */}
        <motion.div
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="bg-canvas-surface border border-canvas-border rounded-xl p-6"
        >
          <h2 className="text-sm font-semibold text-sidebar-muted uppercase tracking-wider mb-5">
            Questions by Type
          </h2>
          <div className="space-y-4">
            {Object.entries(stats.questions_by_type).map(([type, count], i) => {
              const pct = stats.total_questions > 0
                ? ((count / stats.total_questions) * 100).toFixed(1)
                : '0.0';
              const isBlue = type === 'technical';
              return (
                <div key={type}>
                  <div className="flex justify-between items-center mb-1.5">
                    <div className="flex items-center gap-2">
                      <div className={`w-2.5 h-2.5 rounded-full ${isBlue ? 'bg-blue-400' : 'bg-purple-400'}`} />
                      <span className="text-sm font-medium text-sidebar-text capitalize">{type}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-bold text-sidebar-text">{count}</span>
                      <span className="text-xs text-sidebar-muted ml-1.5">({pct}%)</span>
                    </div>
                  </div>
                  <div className="w-full bg-canvas-hover rounded-full h-2 overflow-hidden">
                    <motion.div
                      className={`h-2 rounded-full ${isBlue ? 'bg-blue-400' : 'bg-purple-400'}`}
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.8, delay: 0.3 + i * 0.1 }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>

        {/* By role */}
        <motion.div
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="bg-canvas-surface border border-canvas-border rounded-xl p-6"
        >
          <h2 className="text-sm font-semibold text-sidebar-muted uppercase tracking-wider mb-5">
            Questions by Role
          </h2>
          <div className="space-y-4">
            {Object.entries(stats.questions_by_job_title)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 6)
              .map(([jobTitle, count], i) => {
                const pct = stats.total_questions > 0
                  ? ((count / stats.total_questions) * 100).toFixed(1)
                  : '0.0';
                return (
                  <div key={jobTitle}>
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="text-sm font-medium text-sidebar-text truncate flex-1 mr-4">
                        {jobTitle}
                      </span>
                      <div className="text-right flex-shrink-0">
                        <span className="text-sm font-bold text-sidebar-text">{count}</span>
                        <span className="text-xs text-sidebar-muted ml-1.5">({pct}%)</span>
                      </div>
                    </div>
                    <div className="w-full bg-canvas-hover rounded-full h-2 overflow-hidden">
                      <motion.div
                        className="h-2 rounded-full bg-accent"
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.8, delay: 0.4 + i * 0.08 }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </motion.div>
      </div>

      {/* Insight cards */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.5 }}
        className="grid grid-cols-1 sm:grid-cols-3 gap-4"
      >
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <Target className="w-4 h-4 text-blue-400" />
            </div>
            <h3 className="text-sm font-semibold text-sidebar-text">Coverage</h3>
          </div>
          <p className="text-3xl font-bold text-blue-400 mb-1">
            {Object.keys(stats.questions_by_job_title).length}
          </p>
          <p className="text-xs text-sidebar-muted">Different job roles covered</p>
        </div>

        <div className="bg-accent/10 border border-accent/20 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-accent/20 rounded-lg">
              <Award className="w-4 h-4 text-accent" />
            </div>
            <h3 className="text-sm font-semibold text-sidebar-text">Difficulty</h3>
          </div>
          <p className="text-3xl font-bold text-accent mb-1">
            {stats.average_difficulty.toFixed(1)}/5
          </p>
          <p className="text-xs text-sidebar-muted">Average difficulty level</p>
        </div>

        <div className="bg-orange-500/10 border border-orange-500/20 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-orange-500/20 rounded-lg">
              <Flag className="w-4 h-4 text-orange-400" />
            </div>
            <h3 className="text-sm font-semibold text-sidebar-text">Review Queue</h3>
          </div>
          <p className="text-3xl font-bold text-orange-400 mb-1">{stats.flagged_questions}</p>
          <p className="text-xs text-sidebar-muted">Questions flagged for review</p>
        </div>
      </motion.div>
    </div>
  );
};

export default StatsPage;
