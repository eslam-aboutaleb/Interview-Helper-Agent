import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { MessageSquare, Plus, BarChart3, TrendingUp, Users, Flag, Sparkles, ArrowRight } from 'lucide-react';
import { questionsApi, statsApi, parseAxiosError } from '../services/api';
import { Question, Stats } from '../types';
import { ErrorResponse, ErrorType } from '../services/errorHandler';
import StatCard from '../components/StatCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Alert from '../components/Alert';
import toast from 'react-hot-toast';

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
        questionsApi.getAll({ limit: 5 })
      ]);
      setStats(statsRes.data);
      setRecentQuestions(questionsRes.data);
    } catch (err) {
      const parsedError = parseAxiosError(err);
      setError(parsedError);
      console.error('Failed to fetch dashboard data:', parsedError);
    } finally {
      setLoading(false);
    }
  };

  const getDifficultyColor = (difficulty: number): string => {
    const colors = {
      1: 'bg-success-100 text-success-800',
      2: 'bg-primary-100 text-primary-800',
      3: 'bg-warning-100 text-warning-800',
      4: 'bg-error-100 text-error-800',
      5: 'bg-gray-100 text-gray-800',
    };
    return colors[difficulty as keyof typeof colors] || colors[3];
  };

  const getTypeColor = (type: string): string => {
    return type === 'technical' 
      ? 'bg-blue-100 text-blue-800'
      : 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Error Alert */}
      {error && (
        <Alert
          type="error"
          title="Failed to Load Dashboard"
          message={error.message}
          details={error.details}
          actionLabel="Retry"
          onAction={fetchDashboardData}
          onDismiss={() => setError(null)}
        />
      )}
      {/* Hero Section */}
      <motion.div 
        className="text-center py-16"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <motion.div
          className="inline-flex items-center space-x-2 mb-6"
          initial={{ scale: 0.8 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className="p-4 bg-gradient-to-br from-gray-700 to-gray-800 rounded-2xl shadow-strong">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
        </motion.div>
        
        <motion.h1 
          className="text-5xl md:text-6xl font-bold text-gray-900 mb-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          Welcome to{' '}
          <span className="bg-gradient-to-r from-gray-700 via-gray-800 to-gray-700 bg-clip-text text-transparent">
            InterviewPrep
          </span>
        </motion.h1>
        
        <motion.p 
          className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          Master your interviews with AI-powered question generation. Get personalized technical and behavioral questions 
          tailored to your target role, track your progress, and ace your next interview.
        </motion.p>
      </motion.div>

      {/* Quick Actions */}
      <motion.div 
        className="grid grid-cols-1 md:grid-cols-3 gap-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.5 }}
      >
        {[
          {
            to: '/generate',
            title: 'Generate Questions',
            description: 'Create AI-powered interview questions',
            icon: Plus,
            gradient: 'from-gray-600 to-gray-700',
            hoverColor: 'hover:border-gray-300',
          },
          {
            to: '/questions',
            title: 'Manage Questions',
            description: 'View and organize your questions',
            icon: MessageSquare,
            gradient: 'from-blue-500 to-cyan-600',
            hoverColor: 'hover:border-blue-300',
          },
          {
            to: '/stats',
            title: 'View Statistics',
            description: 'Analyze your preparation progress',
            icon: BarChart3,
            gradient: 'from-green-500 to-emerald-600',
            hoverColor: 'hover:border-green-300',
          },
        ].map((action, index) => (
          <motion.div
            key={action.to}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.6 + index * 0.1 }}
          >
            <Link
              to={action.to}
              className={`block p-6 bg-white rounded-2xl border border-gray-200 ${action.hoverColor} shadow-soft hover:shadow-medium transition-all duration-300 group`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <motion.div 
                    className={`p-3 bg-gradient-to-br ${action.gradient} rounded-xl shadow-medium group-hover:shadow-strong transition-all duration-300`}
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <action.icon className="w-6 h-6 text-white" />
                  </motion.div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 group-hover:text-gray-600 transition-colors duration-200">
                      {action.title}
                    </h3>
                    <p className="text-gray-600">{action.description}</p>
                  </div>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 group-hover:translate-x-1 transition-all duration-200" />
              </div>
            </Link>
          </motion.div>
        ))}
      </motion.div>

      {/* Statistics Cards */}
      {stats && (
        <motion.div 
          className="grid grid-cols-2 md:grid-cols-4 gap-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.8 }}
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
      )}

      {/* Recent Questions */}
      <motion.div 
        className="bg-white rounded-2xl border border-gray-200 p-8 shadow-soft"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 1.0 }}
      >
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Recent Questions</h2>
            <p className="text-gray-600 mt-1">Your latest generated questions</p>
          </div>
          <Link
            to="/questions"
            className="inline-flex items-center space-x-2 text-gray-700 hover:text-gray-900 font-medium transition-colors duration-200 group"
          >
            <span>View all</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-200" />
          </Link>
        </div>

        <div className="space-y-4">
          {recentQuestions.length === 0 ? (
            <motion.div 
              className="text-center py-16"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
            >
              <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                <MessageSquare className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No questions yet</h3>
              <p className="text-gray-600 mb-6">Generate your first set of interview questions to get started</p>
              <Link
                to="/generate"
                className="inline-flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-gray-700 to-gray-800 text-white rounded-xl hover:shadow-strong transition-all duration-300 font-medium"
              >
                <Plus className="w-4 h-4" />
                <span>Generate Questions</span>
              </Link>
            </motion.div>
          ) : (
            recentQuestions.map((question, index) => (
              <motion.div
                key={question.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className="p-4 border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-soft transition-all duration-200"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-3">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getTypeColor(question.question_type)}`}>
                        {question.question_type}
                      </span>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getDifficultyColor(question.difficulty)}`}>
                        Level {question.difficulty}
                      </span>
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                        {question.job_title}
                      </span>
                    </div>
                    <p className="text-gray-900 font-medium leading-relaxed">{question.question_text}</p>
                  </div>
                  {question.is_flagged && (
                    <Flag className="w-4 h-4 text-warning-500 ml-4 flex-shrink-0" />
                  )}
                </div>
              </motion.div>
            ))
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default Dashboard;