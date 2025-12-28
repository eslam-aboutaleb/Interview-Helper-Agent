import axios, { AxiosError } from 'axios';
import toast from 'react-hot-toast';

// Error type enum
export enum ErrorType {
  NETWORK = 'NETWORK_ERROR',
  VALIDATION = 'VALIDATION_ERROR',
  AUTH = 'AUTH_ERROR',
  NOTFOUND = 'NOT_FOUND_ERROR',
  SERVER = 'SERVER_ERROR',
  UNKNOWN = 'UNKNOWN_ERROR'
}

// Error response type (using type instead of interface)
export type ErrorResponse = {
  type: ErrorType;
  message: string;
  statusCode?: number;
  details?: Record<string, any>;
};

// Parse axios error to user-friendly format
export function parseAxiosError(error: unknown): ErrorResponse {
  if (!axios.isAxiosError(error)) {
    return {
      type: ErrorType.UNKNOWN,
      message: 'An unexpected error occurred. Please try again.',
      details: { error }
    };
  }

  const axiosError = error as AxiosError<any>;
  const status = axiosError.response?.status;
  const data = axiosError.response?.data;

  // Network error (no response)
  if (!axiosError.response) {
    return {
      type: ErrorType.NETWORK,
      message: 'Network connection failed. Please check your internet and try again.',
      details: { originalError: axiosError.message }
    };
  }

  // Validation error (400)
  if (status === 400) {
    const message = data?.detail || data?.message || 'Invalid input. Please check the highlighted fields.';
    return {
      type: ErrorType.VALIDATION,
      message,
      statusCode: 400,
      details: data
    };
  }

  // Auth error (401)
  if (status === 401) {
    return {
      type: ErrorType.AUTH,
      message: "You don't have permission to perform this action. Please log in again.",
      statusCode: 401,
      details: data
    };
  }

  // Not found error (404)
  if (status === 404) {
    return {
      type: ErrorType.NOTFOUND,
      message: 'The requested resource was not found. It may have been deleted.',
      statusCode: 404,
      details: data
    };
  }

  // Server error (5xx)
  if (status && status >= 500) {
    return {
      type: ErrorType.SERVER,
      message: 'Server error. Please try again later.',
      statusCode: status,
      details: data
    };
  }

  // Unknown error
  return {
    type: ErrorType.UNKNOWN,
    message: data?.message || 'An error occurred. Please try again.',
    statusCode: status,
    details: data
  };
}

// Show error toast
export function showErrorToast(error: ErrorResponse): void {
  toast.error(error.message, { duration: 5000 });
}

// Log error for debugging
export function logError(error: ErrorResponse, context?: string): void {
  const errorLog = {
    timestamp: new Date().toISOString(),
    context,
    ...error
  };

  if (process.env.NODE_ENV === 'development') {
    console.error('Error Log:', errorLog);
  }
}

// Async error handler wrapper
export async function handleAsyncError<T>(
  asyncFn: () => Promise<T>,
  onError?: (error: ErrorResponse) => void
): Promise<T | null> {
  try {
    return await asyncFn();
  } catch (error) {
    const parsedError = parseAxiosError(error);
    logError(parsedError, 'handleAsyncError');
    if (onError) {
      onError(parsedError);
    }
    return null;
  }
}

// Form validation helper
export function validateFormData(
  data: Record<string, any>,
  rules: Record<string, (value: any) => string | null>
): Record<string, string> {
  const errors: Record<string, string> = {};

  Object.entries(rules).forEach(([field, validator]: [string, any]) => {
    const error = validator(data[field]);
    if (error) {
      errors[field] = error;
    }
  });

  return errors;
}

// Reusable validation rules
export const ValidationRules = {
  required: (fieldName: string) => (value: any) =>
    !value || (typeof value === 'string' && !value.trim())
      ? `${fieldName} is required`
      : null,

  minLength: (fieldName: string, min: number) => (value: any) =>
    value && typeof value === 'string' && value.length < min
      ? `${fieldName} must be at least ${min} characters`
      : null,

  maxLength: (fieldName: string, max: number) => (value: any) =>
    value && typeof value === 'string' && value.length > max
      ? `${fieldName} cannot exceed ${max} characters`
      : null,

  minValue: (fieldName: string, min: number) => (value: any) =>
    value && typeof value === 'number' && value < min
      ? `${fieldName} must be at least ${min}`
      : null,

  maxValue: (fieldName: string, max: number) => (value: any) =>
    value && typeof value === 'number' && value > max
      ? `${fieldName} cannot exceed ${max}`
      : null,

  email: (fieldName: string) => (value: any) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return value && !emailRegex.test(value)
      ? `${fieldName} is not valid`
      : null;
  },

  url: (fieldName: string) => (value: any) => {
    try {
      if (value) new URL(value);
      return null;
    } catch {
      return `${fieldName} is not a valid URL`;
    }
  }
};
