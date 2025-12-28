import axios, { AxiosError, AxiosResponse } from 'axios';
import toast from 'react-hot-toast';
import { Question, QuestionSet, Stats, QuestionGenerateRequest, QuestionCreateRequest, QuestionUpdateRequest } from '../types';
import { parseAxiosError, ErrorResponse } from './errorHandler';

// The baseURL is removed. All requests are now relative to the current domain.
// - On EC2, NGINX will proxy requests starting with /api to the backend.
// - For local development, we will configure the React dev server proxy.
const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Request interceptor - add request tracking
api.interceptors.request.use(
  (config) => {
    // Add timestamp for debugging
    (config as any).timestamp = Date.now();
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - enhanced error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    // Parse and log error
    const parsedError = parseAxiosError(error);
    
    // Log detailed error info in development
    if (process.env.NODE_ENV === 'development') {
      console.error('API Error:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
        config: error.config?.url
      });
    }

    // Don't show duplicate error toasts - let callers handle it
    return Promise.reject(error);
  }
);

/**
 * Wrapper function for API calls with consistent error handling
 */
const handleApiCall = async <T>(
  apiCall: () => Promise<AxiosResponse<T>>
): Promise<{ data: T | null; error: ErrorResponse | null }> => {
  try {
    const response = await apiCall();
    return { data: response.data, error: null };
  } catch (err) {
    const error = parseAxiosError(err);
    return { data: null, error };
  }
};

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

export { parseAxiosError };
export default api;
