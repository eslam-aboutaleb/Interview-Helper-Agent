import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Sparkles } from 'lucide-react';
import { documentsApi, parseAxiosError } from '../services/api';
import { ErrorResponse } from '../services/errorHandler';
import Alert from '../components/Alert';
import EmptyState from '../components/EmptyState';
import { Skeleton } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { SkillGap, UserDocument } from '../types';

const SkillList: React.FC<{
  title: string;
  skills: string[];
  variant: 'success' | 'danger' | 'neutral';
}> = ({ title, skills, variant }) => (
  <div className="bg-white rounded-lg border border-gray-200 p-5">
    <div className="flex items-center justify-between mb-3">
      <h3 className="font-semibold text-gray-900">{title}</h3>
      <Badge variant={variant}>{skills.length}</Badge>
    </div>
    {skills.length === 0 ? (
      <p className="text-sm text-gray-400">None</p>
    ) : (
      <div className="flex flex-wrap gap-2">
        {skills.map((skill) => (
          <span
            key={skill}
            className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700"
          >
            {skill}
          </span>
        ))}
      </div>
    )}
  </div>
);

const SkillGapPage: React.FC = () => {
  const [resumeId, setResumeId] = useState<string>('');
  const [jdId, setJdId] = useState<string>('');

  const { data: documents = [], isLoading } = useQuery<UserDocument[]>({
    queryKey: ['documents'],
    queryFn: () => documentsApi.list().then((r) => r.data),
  });

  const resumes = documents.filter((d) => d.document_type === 'resume');
  const jobs = documents.filter((d) => d.document_type === 'jd');

  const analyze = useMutation<SkillGap, Error, void>({
    mutationFn: () => documentsApi.skillGap(Number(resumeId), Number(jdId)).then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton width={240} height={36} />
        <Skeleton width="100%" height={120} variant="rectangular" />
        <Skeleton width="100%" height={260} variant="rectangular" />
      </div>
    );
  }

  const hasDocuments = resumes.length > 0 && jobs.length > 0;
  const queryError: ErrorResponse | null = analyze.isError ? parseAxiosError(analyze.error) : null;

  if (!hasDocuments) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Skill Gap</h1>
          <p className="mt-2 text-gray-600">
            Compare a resume against a job description to see what to learn next.
          </p>
        </div>
        <EmptyState
          title="Upload documents first"
          message="Skill-gap analysis needs at least one resume and one job description."
          icon={<Sparkles className="w-12 h-12 text-gray-400" />}
          actionLabel="Go to Documents"
          onAction={() => {
            window.location.href = '/documents';
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Skill Gap</h1>
        <p className="mt-2 text-gray-600">
          Compare a resume against a job description to see what to learn next.
        </p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Select
            label="Resume"
            value={resumeId}
            onChange={(e) => setResumeId(e.target.value)}
            options={[
              { value: '', label: 'Select a resume' },
              ...resumes.map((d) => ({
                value: String(d.id),
                label: d.filename || `Resume #${d.id}`,
              })),
            ]}
          />
          <Select
            label="Job description"
            value={jdId}
            onChange={(e) => setJdId(e.target.value)}
            options={[
              { value: '', label: 'Select a job description' },
              ...jobs.map((d) => ({ value: String(d.id), label: d.filename || `Job #${d.id}` })),
            ]}
          />
        </div>

        <div className="mt-6">
          <Button
            onClick={() => analyze.mutate()}
            isLoading={analyze.isPending}
            disabled={!resumeId || !jdId}
            variant="primary"
            size="md"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Analyze
          </Button>
        </div>
      </div>

      {queryError && <Alert type="error" title="Analysis failed" message={queryError.message} />}

      {analyze.data && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-baseline gap-3">
              <span className="text-4xl font-bold text-gray-900">
                {Math.round(analyze.data.match_percentage)}%
              </span>
              <span className="text-sm text-gray-500">skill match</span>
            </div>
            <p className="mt-3 text-gray-700">{analyze.data.summary}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <SkillList
              title="Missing skills"
              skills={analyze.data.missing_skills}
              variant="danger"
            />
            <SkillList
              title="Matched skills"
              skills={analyze.data.matched_skills}
              variant="success"
            />
            <SkillList title="Extra skills" skills={analyze.data.extra_skills} variant="neutral" />
          </div>
        </div>
      )}
    </div>
  );
};

export default SkillGapPage;
