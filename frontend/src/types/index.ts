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