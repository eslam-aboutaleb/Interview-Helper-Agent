import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from 'react-hot-toast';
import { queryClient } from './lib/queryClient';
import Header from './components/Header';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';
import Dashboard from './pages/Dashboard';
import Questions from './pages/Questions';
import Generate from './pages/Generate';
import Interview from './pages/Interview';
import Documents from './pages/Documents';
import SkillGap from './pages/SkillGap';
import LearningPlan from './pages/LearningPlan';

// Stats pulls in recharts (~450 kB minified), which is only needed on
// /stats. Lazy-loading it keeps that weight out of the initial bundle for
// every route that does not render charts.
const Stats = lazy(() => import('./pages/Stats'));

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Router>
          <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100">
            <Header />
            <main className="container mx-auto px-4 py-8 max-w-7xl">
              <Suspense fallback={<LoadingSpinner />}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/questions" element={<Questions />} />
                  <Route path="/generate" element={<Generate />} />
                  <Route path="/interview" element={<Interview />} />
                  <Route path="/stats" element={<Stats />} />
                  <Route path="/documents" element={<Documents />} />
                  <Route path="/skill-gap" element={<SkillGap />} />
                  <Route path="/learning-plan" element={<LearningPlan />} />
                </Routes>
              </Suspense>
            </main>
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: '#363636',
                  color: '#fff',
                },
                success: {
                  duration: 3000,
                  iconTheme: {
                    primary: '#22c55e',
                    secondary: '#fff',
                  },
                },
                error: {
                  duration: 5000,
                  iconTheme: {
                    primary: '#ef4444',
                    secondary: '#fff',
                  },
                },
              }}
            />
          </div>
        </Router>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
