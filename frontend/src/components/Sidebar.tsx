import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  LayoutDashboard,
  MessageSquare,
  Sparkles,
  BarChart3,
  FolderOpen,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface NavItem {
  path: string;
  label: string;
  icon: React.ElementType;
  description: string;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard, description: 'Overview & recent activity' },
  { path: '/generate', label: 'Generate', icon: Sparkles, description: 'AI question generation' },
  { path: '/questions', label: 'Questions', icon: MessageSquare, description: 'Browse & manage questions' },
  { path: '/question-sets', label: 'Question Sets', icon: FolderOpen, description: 'Organized collections' },
  { path: '/stats', label: 'Statistics', icon: BarChart3, description: 'Progress & analytics' },
];

const Sidebar: React.FC = () => {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 260 }}
      transition={{ duration: 0.25, ease: 'easeInOut' }}
      className="flex-shrink-0 h-screen bg-sidebar-bg border-r border-sidebar-border flex flex-col overflow-hidden"
    >
      {/* Logo */}
      <div className="flex items-center h-14 px-4 border-b border-sidebar-border flex-shrink-0">
        <div className="flex items-center space-x-3 min-w-0">
          <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center flex-shrink-0">
            <Brain className="w-4 h-4 text-white" />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <span className="text-sm font-semibold text-sidebar-text whitespace-nowrap">
                  InterviewCoach
                </span>
                <p className="text-xs text-sidebar-muted whitespace-nowrap">AI-Powered Platform</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {navItems.map(({ path, label, icon: Icon, description }) => {
          const active = isActive(path);
          return (
            <Link key={path} to={path} title={collapsed ? label : undefined}>
              <motion.div
                className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-colors duration-150 group cursor-pointer ${
                  active
                    ? 'bg-canvas-surface text-sidebar-text'
                    : 'text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-text'
                }`}
                whileHover={{ x: collapsed ? 0 : 2 }}
                transition={{ duration: 0.1 }}
              >
                <Icon
                  className={`w-5 h-5 flex-shrink-0 ${
                    active ? 'text-accent' : 'text-sidebar-muted group-hover:text-sidebar-text'
                  }`}
                />
                <AnimatePresence>
                  {!collapsed && (
                    <motion.div
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: 'auto' }}
                      exit={{ opacity: 0, width: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden min-w-0"
                    >
                      <p className={`text-sm font-medium whitespace-nowrap ${active ? 'text-sidebar-text' : ''}`}>
                        {label}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
                {active && !collapsed && (
                  <motion.div
                    layoutId="activeIndicator"
                    className="ml-auto w-1.5 h-1.5 rounded-full bg-accent flex-shrink-0"
                  />
                )}
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <div className="px-2 pb-4 flex-shrink-0">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center px-3 py-2.5 rounded-lg text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-text transition-colors duration-150"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <div className="flex items-center space-x-2 w-full">
              <ChevronLeft className="w-4 h-4" />
              <span className="text-sm">Collapse</span>
            </div>
          )}
        </button>
      </div>
    </motion.aside>
  );
};

export default Sidebar;
