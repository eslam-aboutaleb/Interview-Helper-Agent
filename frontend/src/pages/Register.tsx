import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { UserPlus } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ErrorResponse, parseAxiosError } from '../services/errorHandler';
import Alert from '../components/Alert';
import toast from 'react-hot-toast';

const Register: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<ErrorResponse | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!email.trim()) {
      errors.email = 'Email is required';
    } else if (email.trim().length < 3) {
      errors.email = 'Email must be at least 3 characters';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errors.email = 'Email is not valid';
    }

    if (!password) {
      errors.password = 'Password is required';
    } else if (password.length < 8) {
      errors.password = 'Password must be at least 8 characters';
    } else if (password.length > 128) {
      errors.password = 'Password cannot exceed 128 characters';
    }

    if (fullName.trim().length > 200) {
      errors.full_name = 'Full name cannot exceed 200 characters';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      toast.error('Please fix the validation errors');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await register(email.trim(), password, fullName.trim() || undefined);
      toast.success('Account created successfully!');
      navigate('/', { replace: true });
    } catch (err: unknown) {
      setError(parseAxiosError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto space-y-8">
      {error && (
        <Alert
          type="error"
          title="Registration Failed"
          message={error.message}
          details={error.details}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Header */}
      <motion.div
        className="text-center"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="inline-flex items-center space-x-3 mb-6">
          <motion.div
            className="p-4 bg-gradient-to-br from-gray-700 to-gray-800 rounded-2xl shadow-strong"
            whileHover={{ scale: 1.05, rotate: 5 }}
          >
            <UserPlus className="w-8 h-8 text-white" />
          </motion.div>
          <h1 className="text-4xl font-bold text-gray-900">Create Account</h1>
        </div>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          Join InterviewPrep to start your AI-powered interview preparation
        </p>
      </motion.div>

      {/* Registration Form */}
      <motion.div
        className="bg-white rounded-2xl border border-gray-200 p-8 shadow-soft"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-3">Email *</label>
            <input
              type="email"
              name="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              aria-label="Email address"
              autoComplete="email"
              className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:border-blue-500 transition-all duration-200 bg-gray-50 focus:bg-white ${
                validationErrors.email
                  ? 'border-error-300 focus:ring-error-500'
                  : 'border-gray-300 focus:ring-blue-500'
              }`}
            />
            {validationErrors.email && (
              <p className="text-error-600 text-sm mt-2">{validationErrors.email}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-3">Password *</label>
            <input
              type="password"
              name="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              aria-label="Password"
              autoComplete="new-password"
              className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:border-blue-500 transition-all duration-200 bg-gray-50 focus:bg-white ${
                validationErrors.password
                  ? 'border-error-300 focus:ring-error-500'
                  : 'border-gray-300 focus:ring-blue-500'
              }`}
            />
            {validationErrors.password && (
              <p className="text-error-600 text-sm mt-2">{validationErrors.password}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-3">
              Full Name <span className="font-normal text-gray-500">(optional)</span>
            </label>
            <input
              type="text"
              name="full_name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g., Jane Doe"
              aria-label="Full name"
              autoComplete="name"
              className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:border-blue-500 transition-all duration-200 bg-gray-50 focus:bg-white ${
                validationErrors.full_name
                  ? 'border-error-300 focus:ring-error-500'
                  : 'border-gray-300 focus:ring-blue-500'
              }`}
            />
            {validationErrors.full_name && (
              <p className="text-error-600 text-sm mt-2">{validationErrors.full_name}</p>
            )}
          </div>

          <motion.button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex items-center justify-center space-x-3 px-8 py-4 bg-gradient-to-r from-gray-700 to-gray-800 text-white rounded-xl font-semibold shadow-strong hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
            whileHover={{ scale: isSubmitting ? 1 : 1.02 }}
            whileTap={{ scale: isSubmitting ? 1 : 0.98 }}
          >
            {isSubmitting ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                <span>Creating Account...</span>
              </>
            ) : (
              <>
                <UserPlus className="w-5 h-5" />
                <span>Create Account</span>
              </>
            )}
          </motion.button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-blue-600 hover:text-blue-500">
            Sign in here
          </Link>
        </p>
      </motion.div>
    </div>
  );
};

export default Register;
