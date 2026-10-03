import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, CheckCircle2, AlertCircle, Lightbulb } from 'lucide-react';
import { InterviewEvaluation } from '../types';

interface EvaluationCardProps {
  evaluation: InterviewEvaluation;
}

const ScoreBar: React.FC<{ label: string; score: number; color: string }> = ({
  label,
  score,
  color,
}) => (
  <div className="space-y-1">
    <div className="flex justify-between text-sm">
      <span className="text-slate-600">{label}</span>
      <span className="font-semibold text-slate-900">{score.toFixed(1)}</span>
    </div>
    <div className="h-2 bg-slate-200/70 rounded-full overflow-hidden">
      <motion.div
        className={`h-full rounded-full ${color}`}
        initial={{ width: 0 }}
        animate={{ width: `${(score / 10) * 100}%` }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      />
    </div>
  </div>
);

export const EvaluationCard: React.FC<EvaluationCardProps> = ({ evaluation }) => {
  return (
    <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-slate-600" />
          <span className="text-sm font-semibold text-slate-700">Answer Evaluation</span>
        </div>
        <div className="text-2xl font-bold text-slate-900">
          {evaluation.overall_score.toFixed(1)}
          <span className="text-sm font-normal text-slate-500">/10</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ScoreBar label="Technical" score={evaluation.technical_score} color="bg-blue-500" />
        <ScoreBar
          label="Communication"
          score={evaluation.communication_score}
          color="bg-green-500"
        />
        <ScoreBar
          label="Completeness"
          score={evaluation.completeness_score}
          color="bg-purple-500"
        />
        <ScoreBar label="Overall" score={evaluation.overall_score} color="bg-slate-700" />
      </div>

      {evaluation.strengths && evaluation.strengths.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4 text-green-600" />
            <span className="text-sm font-semibold text-green-700">Strengths</span>
          </div>
          <ul className="space-y-1">
            {evaluation.strengths.map((s, i) => (
              <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                <span className="text-green-500 mt-1">•</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {evaluation.gaps && evaluation.gaps.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="w-4 h-4 text-amber-600" />
            <span className="text-sm font-semibold text-amber-700">Areas to improve</span>
          </div>
          <ul className="space-y-1">
            {evaluation.gaps.map((g, i) => (
              <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                <span className="text-amber-500 mt-1">•</span>
                <span>{g}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {evaluation.tips && evaluation.tips.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb className="w-4 h-4 text-blue-600" />
            <span className="text-sm font-semibold text-blue-700">Tips</span>
          </div>
          <ul className="space-y-1">
            {evaluation.tips.map((t, i) => (
              <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                <span className="text-blue-500 mt-1">•</span>
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
