import axios, { AxiosError } from 'axios';
import {
  Question,
  QuestionSet,
  Stats,
  QuestionGenerateRequest,
  QuestionCreateRequest,
  QuestionUpdateRequest,
  QuestionExportFormat,
  QuestionImportSummary,
  QuestionSearchParams,
  InterviewSessionCreate,
  InterviewSession,
  InterviewMessage,
  InterviewAnswerRequest,
  InterviewTurnResponse,
  ModelAnswerRequest,
  ModelAnswerResponse,
  UserDocument,
  SkillGap,
  LearningPlan,
} from '../types';
import { parseAxiosError } from './errorHandler';

// The baseURL is removed. All requests are now relative to the current domain.
// - On EC2, NGINX will proxy requests starting with /api to the backend.
// - For local development, we will configure the React dev server proxy.
const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Response interceptor - enhanced error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    // Log detailed error info in development
    if (import.meta.env.DEV) {
      console.error('API Error:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
        config: error.config?.url,
      });
    }

    // Don't show duplicate error toasts - let callers handle it
    return Promise.reject(error);
  }
);

export const questionsApi = {
  generate: (data: QuestionGenerateRequest) =>
    api.post<Question[]>('/api/questions/generate', data),

  getAll: (params?: QuestionSearchParams) => api.get<Question[]>('/api/questions/', { params }),

  // Server-side full-text search across question text, job title and tags.
  search: (q: string, params?: Omit<QuestionSearchParams, 'q'>) =>
    api.get<Question[]>('/api/questions/', {
      params: { ...params, q },
    }),

  getById: (id: number) => api.get<Question>(`/api/questions/${id}`),

  create: (data: QuestionCreateRequest) => api.post<Question>('/api/questions/', data),

  update: (id: number, data: QuestionUpdateRequest) =>
    api.put<Question>(`/api/questions/${id}`, data),

  delete: (id: number) => api.delete(`/api/questions/${id}`),

  getJobTitles: () => api.get<string[]>('/api/questions/job-titles/'),

  // Distinct companies tagged on questions, for the company filter.
  getCompanies: () => api.get<string[]>('/api/questions/companies/'),

  // Streams the export as a blob so the caller can trigger a file download.
  export: (format: QuestionExportFormat, params?: Omit<QuestionSearchParams, 'q'>) =>
    api.get<Blob>('/api/questions/export', {
      params: { ...params, format },
      responseType: 'blob',
    }),

  // The file is parsed by the caller; the endpoint takes a JSON array.
  importQuestions: (questions: QuestionCreateRequest[]) =>
    api.post<QuestionImportSummary>('/api/questions/import', questions),
};

export const questionSetsApi = {
  getAll: (params?: { skip?: number; limit?: number }) =>
    api.get<QuestionSet[]>('/api/questions/sets/', { params }),

  create: (data: {
    name: string;
    description: string;
    job_title: string;
    question_ids: number[];
  }) => api.post<QuestionSet>('/api/questions/sets', data),
};

export const statsApi = {
  get: () => api.get<Stats>('/api/stats/'),
};

export const learningApi = {
  get: () => api.get<LearningPlan>('/api/learning/plan'),

  regenerate: () => api.post<LearningPlan>('/api/learning/plan'),
};

export const interviewsApi = {
  start: (data: InterviewSessionCreate) =>
    api.post<InterviewSession>('/api/interviews/sessions', data),

  list: (limit?: number) =>
    api.get<InterviewSession[]>('/api/interviews/sessions', {
      params: limit ? { limit } : undefined,
    }),

  get: (sessionId: number) => api.get<InterviewSession>(`/api/interviews/sessions/${sessionId}`),

  getMessages: (sessionId: number) =>
    api.get<InterviewMessage[]>(`/api/interviews/sessions/${sessionId}/messages`),

  submitAnswer: (sessionId: number, data: InterviewAnswerRequest) =>
    api.post<InterviewTurnResponse>(`/api/interviews/sessions/${sessionId}/answer`, data),

  modelAnswer: (data: ModelAnswerRequest) =>
    api.post<ModelAnswerResponse>('/api/interviews/model-answer', data),
};

// Helper function for QuestionSets page
export const fetchQuestionSets = async (): Promise<QuestionSet[]> => {
  const response = await questionSetsApi.getAll();
  return response.data;
};

export type DocumentType = 'resume' | 'jd';

export const documentsApi = {
  // The shared `api` instance defaults to Content-Type: application/json.
  // For multipart uploads the header must be left unset so the browser can
  // generate the multipart boundary itself.
  upload: (documentType: DocumentType, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.post<UserDocument>('/api/documents/upload', form, {
      params: { document_type: documentType },
      headers: { 'Content-Type': undefined },
    });
  },

  list: (documentType?: DocumentType) =>
    api.get<UserDocument[]>('/api/documents/', {
      params: documentType ? { document_type: documentType } : undefined,
    }),

  remove: (documentId: number) => api.delete<void>(`/api/documents/${documentId}`),

  skillGap: (resumeId: number, jdId: number) =>
    api.post<SkillGap>('/api/documents/skill-gap', null, {
      params: { resume_id: resumeId, jd_id: jdId },
    }),
};

export { parseAxiosError };
export default api;
