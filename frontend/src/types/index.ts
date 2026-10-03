export interface Question {
  id: number;
  job_title: string;
  question_text: string;
  question_type: 'technical' | 'behavioral';
  difficulty: number;
  is_flagged: boolean;
  tags?: string;
  created_at: string;
  updated_at?: string;
}

export interface QuestionSet {
  id: number;
  name: string;
  description?: string;
  job_title: string;
  question_ids: string;
  created_at: string;
  updated_at?: string;
}

export interface UserRating {
  id: number;
  question_id: number;
  rating: number;
  feedback?: string;
  created_at: string;
}

export interface Stats {
  total_questions: number;
  questions_by_type: Record<string, number>;
  questions_by_job_title: Record<string, number>;
  average_difficulty: number;
  flagged_questions: number;
  total_question_sets: number;
  /** Signup counts for the last 7 days, ascending by date. */
  signups_last_7_days: { date: string; count: number }[];
  /** Daily evaluation count and mean score; `average_score` is null when the day has none. */
  evaluations_last_7_days: { date: string; average_score: number | null; count: number }[];
  /** One entry per difficulty level, always covering levels 1-5. */
  difficulty_distribution: { difficulty: number; count: number }[];
  /** Weekly mean score over the last 8 ISO weeks; empty when the window has no evaluations. */
  average_score_trend: { week_start: string; average_score: number | null; count: number }[];
}

export interface QuestionGenerateRequest {
  job_title: string;
  count: number;
  question_type: 'technical' | 'behavioral' | 'mixed';
}

export interface QuestionCreateRequest {
  job_title: string;
  question_text: string;
  question_type: 'technical' | 'behavioral';
  difficulty?: number;
  tags?: string;
}

export interface QuestionUpdateRequest {
  difficulty?: number;
  is_flagged?: boolean;
  tags?: string;
}

/* ---------- Mock interview ---------- */

export interface InterviewSessionCreate {
  job_title: string;
  session_type?: 'technical' | 'behavioral' | 'mixed';
  difficulty?: number;
  max_turns?: number;
  document_id?: number | null;
}

export interface InterviewSession {
  id: number;
  user_id: number;
  job_title: string;
  session_type: string;
  difficulty: number;
  target_difficulty: number;
  status: 'active' | 'completed';
  current_turn: number;
  max_turns: number;
  created_at: string;
  updated_at?: string | null;
  completed_at?: string | null;
}

export interface InterviewMessage {
  id: number;
  session_id: number;
  role: 'interviewer' | 'candidate' | 'system';
  content: string;
  created_at: string;
}

export interface InterviewAnswerRequest {
  answer: string;
}

export interface InterviewEvaluation {
  overall_score: number;
  technical_score: number;
  communication_score: number;
  completeness_score: number;
  strengths?: string[];
  gaps?: string[];
  tips?: string[];
  next_action?: string;
}

export interface InterviewTurnResponse {
  completed: boolean;
  next_question: string | null;
  evaluation: InterviewEvaluation;
  current_difficulty: number | null;
  turn: number | null;
  summary: Record<string, unknown> | null;
}

export interface ModelAnswerRequest {
  question: string;
  question_type?: 'technical' | 'behavioral';
}

export interface ModelAnswerResponse {
  question: string;
  model_answer: string | null;
}

export interface UserDocument {
  id: number;
  user_id: number;
  document_type: string;
  filename: string | null;
  parsed_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface SkillGap {
  match_percentage: number;
  matched_skills: string[];
  missing_skills: string[];
  extra_skills: string[];
  summary: string;
}

/* ---------- Question search, export and import (Plan 09) ---------- */

export type QuestionExportFormat = 'json' | 'csv';

export interface QuestionSearchParams {
  q?: string;
  skip?: number;
  limit?: number;
  job_title?: string;
  question_type?: string;
  flagged_only?: boolean;
}

export interface QuestionImportError {
  index: number;
  error: string;
}

export interface QuestionImportSummary {
  imported: number;
  skipped: number;
  errors: QuestionImportError[];
}
