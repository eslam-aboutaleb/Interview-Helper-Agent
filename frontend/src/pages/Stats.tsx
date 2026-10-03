import React from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  PieChart,
  TrendingUp,
  Users,
  MessageSquare,
  Flag,
  Target,
  Award,
  Activity,
  BarChart2,
  Radar as RadarIcon,
  LineChart as LineChartIcon,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { statsApi, parseAxiosError } from '../services/api';
import { Stats } from '../types';
import { ErrorResponse } from '../services/errorHandler';
import StatCard from '../components/StatCard';
import Alert from '../components/Alert';
import EmptyState from '../components/EmptyState';
import { Skeleton, SkeletonStatCard } from '../components/ui/Skeleton';

type SignupPoint = Stats['signups_last_7_days'][number];
type EvaluationPoint = Stats['evaluations_last_7_days'][number];
type DifficultyPoint = Stats['difficulty_distribution'][number];
type TrendPoint = Stats['average_score_trend'][number];

/** Height of every chart body. It matches `min-h-96` so the EmptyState and the
 * ResponsiveContainer occupy the same space and swapping between them never
 * shifts the layout. */
const CHART_HEIGHT = 384;

const COLORS = {
  blue: '#3b82f6',
  emerald: '#10b981',
  orange: '#f97316',
  grid: '#e5e7eb',
  muted: '#9ca3af',
  label: '#4b5563',
};

const AXIS_TICK = { fill: COLORS.label, fontSize: 12 };

const TOOLTIP_STYLE = {
  backgroundColor: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: '0.5rem',
  fontSize: '0.75rem',
  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
};

/**
 * Format a `YYYY-MM-DD` bucket key as a short label.
 *
 * The value is parsed manually and formatted in UTC so a bucket never slides to
 * the neighbouring day for users in negative UTC offsets.
 */
const formatBucketLabel = (value: string): string => {
  const [year, month, day] = value.split('-').map(Number);
  if (!year || !month || !day) {
    return value;
  }
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  });
};

const toActivitySeries = (signups: SignupPoint[], evaluations: EvaluationPoint[]) =>
  signups.map((signup, index) => ({
    label: formatBucketLabel(signup.date),
    signups: signup.count,
    evaluations: evaluations[index]?.count ?? 0,
  }));

const toDifficultySeries = (distribution: DifficultyPoint[]) =>
  distribution.map((point) => ({
    label: `Level ${point.difficulty}`,
    count: point.count,
  }));

const toTypeSeries = (questionsByType: Record<string, number>) =>
  Object.entries(questionsByType).map(([type, count]) => ({
    type: type.charAt(0).toUpperCase() + type.slice(1),
    questions: count,
  }));

const toTrendSeries = (trend: TrendPoint[]) =>
  trend.map((point) => ({
    label: formatBucketLabel(point.week_start),
    average_score: point.average_score,
    count: point.count,
  }));

interface ChartCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  iconClassName: string;
  delay: number;
  children: React.ReactNode;
}

const ChartCard: React.FC<ChartCardProps> = ({
  title,
  description,
  icon,
  iconClassName,
  delay,
  children,
}) => (
  <motion.div
    className="bg-white rounded-2xl border border-gray-200 p-8 shadow-soft"
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay }}
  >
    <div className="flex items-center space-x-3">
      <div className={`p-2 rounded-xl ${iconClassName}`}>{icon}</div>
      <h3 className="text-xl font-bold text-gray-900">{title}</h3>
    </div>
    <p className="text-sm text-gray-500 mt-2 mb-6">{description}</p>
    <div className="min-h-96">{children}</div>
  </motion.div>
);

const StatsPage: React.FC = () => {
  const {
    data: stats,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<Stats>({
    queryKey: ['stats'],
    queryFn: () => statsApi.get().then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="text-center">
          <Skeleton width={280} height={40} className="mx-auto" />
          <Skeleton width={420} height={24} className="mx-auto mt-4" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[0, 1, 2, 3].map((i) => (
            <SkeletonStatCard key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {[0, 1].map((i) => (
            <div
              key={i}
              className="bg-white rounded-2xl border border-slate-200 p-8 shadow-soft space-y-6"
            >
              <Skeleton width="40%" height={28} />
              {[0, 1, 2].map((j) => (
                <div key={j} className="space-y-2">
                  <Skeleton width="60%" height={16} />
                  <Skeleton width="100%" height={12} />
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    const parsedError: ErrorResponse = parseAxiosError(error);
    return (
      <Alert
        type="error"
        title="Failed to Load Statistics"
        message={parsedError.message}
        details={parsedError.details}
        actionLabel="Retry"
        onAction={() => refetch()}
      />
    );
  }

  if (!stats) {
    return (
      <EmptyState
        title="No statistics available"
        message="Start generating and rating questions to see your statistics."
        icon={<BarChart3 className="w-12 h-12 text-gray-400" />}
        actionLabel="Generate Questions"
        onAction={() => (window.location.href = '/generate')}
      />
    );
  }

  // Chart series. Each one is derived from the dense (zero-filled) buckets the
  // API returns, so a quiet day reads as a real zero rather than a gap.
  const activitySeries = toActivitySeries(stats.signups_last_7_days, stats.evaluations_last_7_days);
  const difficultySeries = toDifficultySeries(stats.difficulty_distribution);
  const typeSeries = toTypeSeries(stats.questions_by_type);
  const trendSeries = toTrendSeries(stats.average_score_trend);

  const hasQuestions = stats.total_questions > 0;
  const hasActivity = activitySeries.some((point) => point.signups > 0 || point.evaluations > 0);
  const hasEvaluations = trendSeries.some((point) => point.count > 0);

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
          Track your interview preparation progress and analyze question patterns to optimize your
          study plan
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
                      <div
                        className={`w-3 h-3 rounded-full ${
                          type === 'technical' ? 'bg-blue-500' : 'bg-gray-500'
                        }`}
                      />
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
              .sort(([, a], [, b]) => b - a)
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
                      <span className="font-semibold text-gray-700 truncate flex-1 mr-4">
                        {jobTitle}
                      </span>
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
          <p className="text-4xl font-bold mb-2">
            {Object.keys(stats.questions_by_job_title).length}
          </p>
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

      {/* Charts */}
      <motion.div
        className="space-y-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.8 }}
      >
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900">Trends</h2>
          <p className="text-gray-600 mt-2">
            How your question bank and interview practice are evolving over time
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <ChartCard
            title="Questions by Type"
            description="Share of the question bank per interview type"
            icon={<RadarIcon className="w-5 h-5 text-blue-600" />}
            iconClassName="bg-blue-100"
            delay={0.85}
          >
            {hasQuestions ? (
              <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                <RadarChart data={typeSeries} outerRadius="70%">
                  <PolarGrid stroke={COLORS.grid} />
                  <PolarAngleAxis dataKey="type" tick={AXIS_TICK} />
                  <Radar
                    name="Questions"
                    dataKey="questions"
                    stroke={COLORS.blue}
                    strokeWidth={2}
                    fill={COLORS.blue}
                    fillOpacity={0.35}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="No questions yet"
                message="Generate a question set and the type breakdown will appear here."
                icon={<RadarIcon className="w-12 h-12 text-gray-400" />}
              />
            )}
          </ChartCard>

          <ChartCard
            title="Difficulty Distribution"
            description="Question count per difficulty level"
            icon={<BarChart2 className="w-5 h-5 text-green-600" />}
            iconClassName="bg-green-100"
            delay={0.95}
          >
            {hasQuestions ? (
              <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                <BarChart data={difficultySeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} vertical={false} />
                  <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} />
                  <YAxis
                    allowDecimals={false}
                    tick={AXIS_TICK}
                    axisLine={false}
                    tickLine={false}
                    width={40}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: '#f3f4f6' }} />
                  <Bar
                    dataKey="count"
                    name="Questions"
                    fill={COLORS.emerald}
                    radius={[8, 8, 0, 0]}
                    maxBarSize={64}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="No questions yet"
                message="Generate a question set to see how the levels are spread."
                icon={<BarChart2 className="w-12 h-12 text-gray-400" />}
              />
            )}
          </ChartCard>

          <ChartCard
            title="Last 7 Days"
            description="Daily signups and recorded answer evaluations"
            icon={<Activity className="w-5 h-5 text-orange-600" />}
            iconClassName="bg-orange-100"
            delay={1.05}
          >
            {hasActivity ? (
              <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                <AreaChart data={activitySeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} vertical={false} />
                  <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} />
                  <YAxis
                    allowDecimals={false}
                    tick={AXIS_TICK}
                    axisLine={false}
                    tickLine={false}
                    width={40}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '0.75rem' }} />
                  <Area
                    type="monotone"
                    dataKey="signups"
                    name="Signups"
                    stroke={COLORS.blue}
                    strokeWidth={2}
                    fill={COLORS.blue}
                    fillOpacity={0.25}
                  />
                  <Area
                    type="monotone"
                    dataKey="evaluations"
                    name="Evaluations"
                    stroke={COLORS.orange}
                    strokeWidth={2}
                    fill={COLORS.orange}
                    fillOpacity={0.25}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="No activity yet"
                message="Signups and evaluations from the past week will show up here."
                icon={<Activity className="w-12 h-12 text-gray-400" />}
              />
            )}
          </ChartCard>

          <ChartCard
            title="Score Trend"
            description="Weekly average answer score over the last 8 weeks"
            icon={<LineChartIcon className="w-5 h-5 text-blue-600" />}
            iconClassName="bg-blue-100"
            delay={1.15}
          >
            {hasEvaluations ? (
              <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                <LineChart data={trendSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} vertical={false} />
                  <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} />
                  <YAxis
                    domain={[0, 10]}
                    tick={AXIS_TICK}
                    axisLine={false}
                    tickLine={false}
                    width={40}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Line
                    type="monotone"
                    dataKey="average_score"
                    name="Average score"
                    stroke={COLORS.emerald}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                    connectNulls={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="No evaluations yet"
                message="Complete a mock interview and your weekly score trend will appear here."
                icon={<LineChartIcon className="w-12 h-12 text-gray-400" />}
              />
            )}
          </ChartCard>
        </div>
      </motion.div>
    </div>
  );
};

export default StatsPage;
