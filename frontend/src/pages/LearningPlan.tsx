import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, ClipboardList, GraduationCap, RefreshCw, Sparkles } from 'lucide-react';
import { learningApi, parseAxiosError } from '../services/api';
import { ErrorResponse } from '../services/errorHandler';
import Alert from '../components/Alert';
import EmptyState from '../components/EmptyState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader } from '../components/ui/Card';
import { Skeleton } from '../components/ui/Skeleton';
import { LearningPlan, LearningPlanItem, LearningPlanPriority } from '../types';
import toast from 'react-hot-toast';

const PRIORITY_BADGE: Record<LearningPlanPriority, 'danger' | 'warning' | 'neutral'> = {
  high: 'danger',
  medium: 'warning',
  low: 'neutral',
};

const PRIORITY_LABEL: Record<LearningPlanPriority, string> = {
  high: 'High priority',
  medium: 'Medium priority',
  low: 'Low priority',
};

const PlanItem: React.FC<{ item: LearningPlanItem; index: number }> = ({ item, index }) => (
  <motion.div
    className="flex gap-4 rounded-lg border border-slate-200 bg-white p-5"
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.3, delay: index * 0.05 }}
  >
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-800 text-sm font-semibold text-white">
      {index + 1}
    </div>
    <div className="min-w-0 flex-1">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold text-gray-900">{item.topic}</h3>
        <Badge variant={PRIORITY_BADGE[item.priority]}>{PRIORITY_LABEL[item.priority]}</Badge>
        <span className="text-sm text-gray-500">
          {item.estimated_hours} {item.estimated_hours === 1 ? 'hour' : 'hours'}
        </span>
      </div>
      {item.reason && <p className="mt-2 text-sm text-gray-700">{item.reason}</p>}
      {item.recommended_question_ids.length > 0 && (
        <p className="mt-3 text-sm text-gray-600">
          Practice questions:{' '}
          <span className="font-medium text-gray-800">
            {item.recommended_question_ids.join(', ')}
          </span>
        </p>
      )}
    </div>
  </motion.div>
);

const LearningPlanPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [completed, setCompleted] = useState<number[]>([]);

  const {
    data: plan,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<LearningPlan>({
    queryKey: ['learning-plan'],
    queryFn: () => learningApi.get().then((r) => r.data),
  });

  const regenerate = useMutation<LearningPlan, Error, void>({
    mutationFn: () => learningApi.regenerate().then((r) => r.data),
    onSuccess: (data) => {
      toast.success(`Regenerated ${data.items.length} plan item(s)`);
      setCompleted([]);
      queryClient.setQueryData(['learning-plan'], data);
    },
    onError: (err: unknown) => {
      const parsed = parseAxiosError(err);
      toast.error(`Failed to regenerate plan: ${parsed.message}`);
    },
  });

  const toggleCompleted = (index: number) => {
    setCompleted((prev) =>
      prev.includes(index) ? prev.filter((value) => value !== index) : [...prev, index]
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton width={260} height={36} />
        <Skeleton width="100%" height={120} variant="rectangular" />
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} width="100%" height={96} variant="rectangular" />
        ))}
      </div>
    );
  }

  const queryError: ErrorResponse | null = isError ? parseAxiosError(error) : null;

  if (!plan) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Learning Plan</h1>
          <p className="mt-2 text-gray-600">
            A study roadmap built from your skill gaps and weak spots.
          </p>
        </div>
        <Alert
          type="error"
          title="Failed to Load Learning Plan"
          message={queryError?.message ?? 'The learning plan is unavailable.'}
          actionLabel="Retry"
          onAction={() => refetch()}
        />
      </div>
    );
  }

  const hasItems = plan.items.length > 0;

  return (
    <div className="space-y-6">
      {queryError && (
        <Alert
          type="error"
          title="Failed to Refresh Learning Plan"
          message={queryError.message}
          actionLabel="Retry"
          onAction={() => refetch()}
        />
      )}

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <GraduationCap className="h-8 w-8 text-slate-700" aria-hidden="true" />
            <h1 className="text-3xl font-bold text-gray-900">Learning Plan</h1>
          </div>
          <p className="mt-2 text-gray-600">
            A study roadmap built from your skill gaps and weak spots.
          </p>
        </div>
        <Button
          onClick={() => regenerate.mutate()}
          isLoading={regenerate.isPending}
          variant="primary"
          size="md"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Regenerate
        </Button>
      </div>

      <Card>
        <CardHeader className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-gray-800">{plan.summary}</p>
          <Badge variant={plan.source === 'llm' ? 'primary' : 'neutral'}>
            {plan.source === 'llm' ? 'AI generated' : 'Rule-based'}
          </Badge>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-6 text-sm text-gray-600">
          {plan.skill_match_percentage !== null && (
            <span>
              <span className="font-semibold text-gray-900">
                {Math.round(plan.skill_match_percentage)}%
              </span>{' '}
              skill match
            </span>
          )}
          {plan.missing_skills.length > 0 && (
            <span>
              <span className="font-semibold text-gray-900">{plan.missing_skills.length}</span>{' '}
              missing skill(s): {plan.missing_skills.join(', ')}
            </span>
          )}
          <span>
            Updated{' '}
            <span className="font-semibold text-gray-900">
              {new Date(plan.generated_at).toLocaleString()}
            </span>
          </span>
        </CardContent>
      </Card>

      {!hasItems ? (
        <EmptyState
          title="Nothing to study yet"
          message="Upload a resume and a job description, or run a mock interview, and regenerate the plan to get a study roadmap."
          icon={<ClipboardList className="h-12 w-12 text-gray-400" />}
          actionLabel="Regenerate Plan"
          actionLoading={regenerate.isPending}
          onAction={() => regenerate.mutate()}
        />
      ) : (
        <>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <CheckCircle2 className="h-4 w-4 text-green-600" aria-hidden="true" />
            <span>
              {completed.length} of {plan.items.length} topic(s) completed
            </span>
          </div>
          <ol className="space-y-3">
            {plan.items.map((item, index) => (
              <li key={`${item.topic}-${index}`} className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id={`plan-item-${index}`}
                  checked={completed.includes(index)}
                  onChange={() => toggleCompleted(index)}
                  className="mt-1.5 h-4 w-4 rounded border-slate-300 text-slate-700 focus:ring-slate-400"
                />
                <div className="min-w-0 flex-1">
                  <PlanItem item={item} index={index} />
                </div>
              </li>
            ))}
          </ol>
        </>
      )}

      {plan.weak_question_types.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center space-x-2">
              <Sparkles className="h-5 w-5 text-slate-600" aria-hidden="true" />
              <h2 className="font-semibold text-gray-900">Average scores by question type</h2>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {plan.weak_question_types.map((area) => (
                <li key={area.question_type} className="flex items-center justify-between text-sm">
                  <span className="capitalize text-gray-700">{area.question_type}</span>
                  <span className="text-gray-600">
                    {area.average_score !== null ? `${area.average_score}/10` : 'no scores'} ·{' '}
                    {area.sample_size} answer(s)
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default LearningPlanPage;
