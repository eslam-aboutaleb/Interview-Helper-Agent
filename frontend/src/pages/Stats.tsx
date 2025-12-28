import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, PieChart, TrendingUp, Users, MessageSquare, Flag, Target, Award, RefreshCw } from 'lucide-react';
import { statsApi, parseAxiosError } from '../services/api';
import { Stats } from '../types';
import { ErrorResponse, ErrorType } from '../services/errorHandler';
import StatCard from '../components/StatCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Alert from '../components/Alert';
import EmptyState from '../components/EmptyState';
import toast from 'react-hot-toast';

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
      const parsedError = parseAxiosError(err);
      setError(parsedError);
      console.error('Failed to fetch stats:', parsedError);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Alert
          type="error"
          title="Failed to Load Statistics"
          message={error.message}
          details={error.details}
          actionLabel="Retry"
          onAction={fetchStats}
          onDismiss={() => setError(null)}
        />
      </div>
    );
  }

  if (!stats) {
    return (
      <EmptyState
        title="No statistics available"
        message="Start generating and rating questions to see your statistics."
        icon={<BarChart3 className="w-12 h-12 text-gray-400" />}
        actionLabel="Generate Questions"
        onAction={() => window.location.href = '/generate'}
      />
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div 
        className="text-center"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="inline-flex items-center space-x-3 mb-6">
          <motion.div 
            className="p-4 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl shadow-strong"
            whileHover={{ scale: 1.05, rotate: 5 }}
          >
            <BarChart3 className="w-8 h-8 text-white" />
          </motion.div>
          <h1 className="text-4xl font-bold text-gray-900">Statistics Dashboard</h1>
        </div>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          Track your interview preparation progress and analyze question patterns to optimize your study plan
        </p>
      </motion.div>

      {/* Overview Cards */}
      <motion.div 
        className="grid grid-cols-2 md:grid-cols-4 gap-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        <StatCard
          title="Total Questions"
          value={stats.total_questions}
          subtitle="Questions generated"
          icon={MessageSquare}
          color="blue"
          index={0}
        />
        <StatCard
          title="Avg Difficulty"
          value={stats.average_difficulty.toFixed(1)}
          subtitle="Out of 5.0"
          icon={TrendingUp}
          color="green"
          index={1}
        />
        <StatCard
          title="Flagged"
          value={stats.flagged_questions}
          subtitle="Need review"
          icon={Flag}
          color="orange"
          index={2}
        />
        <StatCard
          title="Question Sets"
          value={stats.total_question_sets}
          subtitle="Collections created"
          icon={Users}
          color="gray"
          index={3}
        />
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Questions by Type */}
        <motion.div 
          className="bg-white rounded-2xl border border-gray-200 p-8 shadow-soft"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          <div className="flex items-center space-x-3 mb-8">
            <div className="p-2 bg-gray-100 rounded-xl">
              <PieChart className="w-6 h-6 text-gray-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Questions by Type</h2>
          </div>

          <div className="space-y-6">
            {Object.entries(stats.questions_by_type).map(([type, count], index) => {
              const percentage = ((count / stats.total_questions) * 100).toFixed(1);
              return (
                <motion.div 
                  key={type} 
                  className="space-y-3"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.4, delay: 0.4 + index * 0.1 }}
                >
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                      <div className={`w-3 h-3 rounded-full ${
                        type === 'technical' ? 'bg-blue-500' : 'bg-gray-500'
                      }`} />
                      <span className="capitalize font-semibold text-gray-700">{type}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-lg font-bold text-gray-900">{count}</span>
                      <span className="text-sm text-gray-500 ml-2">({percentage}%)</span>
                    </div>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <motion.div
                      className={`h-3 rounded-full ${
                        type === 'technical' 
                          ? 'bg-gradient-to-r from-blue-500 to-blue-600' 
                          : 'bg-gradient-to-r from-gray-500 to-gray-600'
                      }`}
                      initial={{ width: 0 }}
                      animate={{ width: `${percentage}%` }}
                      transition={{ duration: 1, delay: 0.5 + index * 0.1 }}
                    />
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* Questions by Job Title */}
        <motion.div 
          className="bg-white rounded-2xl border border-gray-200 p-8 shadow-soft"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <div className="flex items-center space-x-3 mb-8">
            <div className="p-2 bg-green-100 rounded-xl">
              <Users className="w-6 h-6 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Questions by Role</h2>
          </div>

          <div className="space-y-6">
            {Object.entries(stats.questions_by_job_title)
              .sort(([,a], [,b]) => b - a)
              .slice(0, 8)
              .map(([jobTitle, count], index) => {
                const percentage = ((count / stats.total_questions) * 100).toFixed(1);
                return (
                  <motion.div 
                    key={jobTitle} 
                    className="space-y-3"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.4, delay: 0.5 + index * 0.1 }}
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-gray-700 truncate flex-1 mr-4">{jobTitle}</span>
                      <div className="text-right">
                        <span className="text-lg font-bold text-gray-900">{count}</span>
                        <span className="text-sm text-gray-500 ml-2">({percentage}%)</span>
                      </div>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                      <motion.div
                        className="bg-gradient-to-r from-green-500 to-emerald-600 h-3 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${percentage}%` }}
                        transition={{ duration: 1, delay: 0.6 + index * 0.1 }}
                      />
                    </div>
                  </motion.div>
                );
              })}
          </div>
        </motion.div>
      </div>

      {/* Additional Insights */}
      <motion.div 
        className="grid grid-cols-1 md:grid-cols-3 gap-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.6 }}
      >
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 p-8 rounded-2xl text-white shadow-strong">
          <div className="flex items-center space-x-4 mb-6">
            <div className="p-3 bg-white/20 rounded-xl">
              <Target className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold">Question Coverage</h3>
          </div>
          <p className="text-4xl font-bold mb-2">{Object.keys(stats.questions_by_job_title).length}</p>
          <p className="text-blue-100">Different job roles covered</p>
        </div>

        <div className="bg-gradient-to-br from-gray-700 to-gray-800 p-8 rounded-2xl text-white shadow-strong">
          <div className="flex items-center space-x-4 mb-6">
            <div className="p-3 bg-white/20 rounded-xl">
              <Award className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold">Difficulty Range</h3>
          </div>
          <p className="text-4xl font-bold mb-2">{stats.average_difficulty.toFixed(1)}/5</p>
          <p className="text-gray-100">Average difficulty level</p>
        </div>

        <div className="bg-gradient-to-br from-orange-500 to-orange-600 p-8 rounded-2xl text-white shadow-strong">
          <div className="flex items-center space-x-4 mb-6">
            <div className="p-3 bg-white/20 rounded-xl">
              <Flag className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold">Review Queue</h3>
          </div>
          <p className="text-4xl font-bold mb-2">{stats.flagged_questions}</p>
          <p className="text-orange-100">Questions flagged for review</p>
        </div>
      </motion.div>
    </div>
  );
};

export default StatsPage;