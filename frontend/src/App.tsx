import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Sidebar from './components/Sidebar';
import ErrorBoundary from './components/ErrorBoundary';
import Dashboard from './pages/Dashboard';
import Questions from './pages/Questions';
import Generate from './pages/Generate';
import Stats from './pages/Stats';
import QuestionSets from './pages/QuestionSets';

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <div className="flex h-screen bg-canvas-bg text-sidebar-text overflow-hidden">
          {/* Dark sidebar */}
          <Sidebar />

          {/* Main content area */}
          <main className="flex-1 overflow-y-auto bg-canvas-bg">
            <div className="max-w-4xl mx-auto px-6 py-8">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/questions" element={<Questions />} />
                <Route path="/generate" element={<Generate />} />
                <Route path="/stats" element={<Stats />} />
                <Route path="/question-sets" element={<QuestionSets />} />
              </Routes>
            </div>
          </main>
        </div>

        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#2f2f2f',
              color: '#ececec',
              border: '1px solid #3d3d3d',
              borderRadius: '10px',
              fontSize: '14px',
            },
            success: {
              duration: 3000,
              iconTheme: {
                primary: '#10a37f',
                secondary: '#2f2f2f',
              },
            },
            error: {
              duration: 5000,
              iconTheme: {
                primary: '#ef4444',
                secondary: '#2f2f2f',
              },
            },
          }}
        />
      </Router>
    </ErrorBoundary>
  );
}

export default App;
