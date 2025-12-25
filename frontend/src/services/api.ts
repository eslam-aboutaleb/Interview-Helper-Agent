import axios from 'axios';
import { Question, QuestionSet, Stats, QuestionGenerateRequest, QuestionCreateRequest, QuestionUpdateRequest } from '../types';

// The baseURL is removed. All requests are now relative to the current domain.
// - On EC2, NGINX will proxy requests starting with /api to the backend.
// - For local development, we will configure the React dev server proxy.
const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor (no changes needed)
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor (no changes needed)
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// The API calls are already correctly using the /api prefix, so no changes are needed here.
export const questionsApi = {
  generate: (data: QuestionGenerateRequest) =>
    api.post<Question[]>('/api/questions/generate', data),

  getAll: (params?: {
    skip?: number;
    limit?: number;
    job_title?: string;
    question_type?: string;
    flagged_only?: boolean;
  }) => api.get<Question[]>('/api/questions/', { params }),

  getById: (id: number) =>
    api.get<Question>(`/api/questions/${id}`),

  create: (data: QuestionCreateRequest) =>
    api.post<Question>('/api/questions/', data),

  update: (id: number, data: QuestionUpdateRequest) =>
    api.put<Question>(`/api/questions/${id}`, data),

  delete: (id: number) =>
    api.delete(`/api/questions/${id}`),

  getJobTitles: () =>
    api.get<string[]>('/api/questions/job-titles/'),
};

export const questionSetsApi = {
  getAll: (params?: {
    skip?: number;
    limit?: number;
  }) => api.get<QuestionSet[]>('/api/questions/sets/', { params }),

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

// Helper function for QuestionSets page
export const fetchQuestionSets = async (): Promise<QuestionSet[]> => {
  const response = await questionSetsApi.getAll();
  return response.data;
};

export default api;

