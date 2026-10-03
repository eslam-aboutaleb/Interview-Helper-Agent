import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Brain,
  Home,
  MessageSquare,
  Plus,
  BarChart3,
  Video,
  FileText,
  Sparkles,
  GraduationCap,
  LogIn,
  UserPlus,
  LogOut,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

const Header: React.FC = () => {
  const location = useLocation();
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/questions', label: 'Questions', icon: MessageSquare },
    { path: '/generate', label: 'Generate', icon: Plus },
    { path: '/interview', label: 'Mock Interview', icon: Video },
    { path: '/stats', label: 'Statistics', icon: BarChart3 },
    { path: '/documents', label: 'Documents', icon: FileText },
    { path: '/skill-gap', label: 'Skill Gap', icon: Sparkles },
    { path: '/learning-plan', label: 'Learning Plan', icon: GraduationCap },
  ];

  const isActive = (path: string) => location.pathname === path;

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
    }
  };

  // Auth actions adapt to the session state. Text labels are hidden
  // below `lg` so the compact mobile bar stays icon-only.
  const authActions = isLoading ? null : isAuthenticated ? (
    <>
      <span className="hidden lg:block text-sm font-medium text-gray-600 max-w-[200px] truncate">
        {user?.email}
      </span>
      <motion.button
        type="button"
        onClick={handleLogout}
        disabled={isLoggingOut}
        className="flex items-center space-x-2 px-4 py-2 rounded-xl text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        aria-label="Logout"
      >
        <LogOut className="w-4 h-4" />
        <span className="font-medium hidden lg:inline">Logout</span>
      </motion.button>
    </>
  ) : (
    <>
      <Link to="/login" aria-label="Login">
        <motion.div
          className="flex items-center space-x-2 px-4 py-2 rounded-xl text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-all duration-200"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <LogIn className="w-4 h-4" />
          <span className="font-medium hidden lg:inline">Login</span>
        </motion.div>
      </Link>
      <Link to="/register" aria-label="Register">
        <motion.div
          className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-gray-700 to-gray-800 text-white shadow-soft hover:shadow-medium transition-all duration-200"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <UserPlus className="w-4 h-4" />
          <span className="font-medium hidden lg:inline">Register</span>
        </motion.div>
      </Link>
    </>
  );

  return (
    <header className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 sticky top-0 z-50 shadow-soft">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3 group">
            <motion.div
              className="p-2 bg-gradient-to-br from-gray-700 to-gray-800 rounded-xl shadow-medium group-hover:shadow-strong transition-all duration-300"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Brain className="w-6 h-6 text-white" />
            </motion.div>
            <div className="flex flex-col">
              <span className="text-xl font-bold bg-gradient-to-r from-gray-700 to-gray-800 bg-clip-text text-transparent">
                InterviewPrep
              </span>
              <span className="text-xs text-gray-500 -mt-1">AI-Powered Platform</span>
            </div>
          </Link>

          <div className="flex items-center space-x-2">
            {/* Navigation */}
            <nav className="hidden md:flex items-center space-x-2">
              {navItems.map(({ path, label, icon: Icon }) => (
                <Link key={path} to={path} className="relative group">
                  <motion.div
                    className={`flex items-center space-x-2 px-4 py-2 rounded-xl transition-all duration-200 ${
                      isActive(path)
                        ? 'bg-gradient-to-r from-gray-100 to-gray-200 text-gray-800 shadow-soft'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="font-medium">{label}</span>
                  </motion.div>
                  {isActive(path) && (
                    <motion.div
                      className="absolute bottom-0 left-1/2 w-1 h-1 bg-gradient-to-r from-gray-700 to-gray-800 rounded-full"
                      layoutId="activeIndicator"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      style={{ transform: 'translateX(-50%)' }}
                    />
                  )}
                </Link>
              ))}
            </nav>

            {/* Auth actions (desktop) */}
            <div className="hidden md:flex items-center space-x-2">{authActions}</div>

            {/* Mobile navigation + auth */}
            <div className="md:hidden">
              <div className="flex items-center space-x-1">
                {navItems.map(({ path, icon: Icon }) => (
                  <Link
                    key={path}
                    to={path}
                    className={`p-2 rounded-lg transition-all duration-200 ${
                      isActive(path)
                        ? 'bg-gradient-to-r from-gray-100 to-gray-200 text-gray-800'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                  </Link>
                ))}
                {authActions}
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
