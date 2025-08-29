import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search, Filter, MessageSquare, SlidersHorizontal } from 'lucide-react';
import { questionsApi } from '../services/api';
import { Question } from '../types';
import QuestionCard from '../components/QuestionCard';
import LoadingSpinner from '../components/LoadingSpinner';
import toast from 'react-hot-toast';

const Questions: React.FC = () => {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [filteredQuestions, setFilteredQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [selectedJobTitle, setSelectedJobTitle] = useState('all');
  const [jobTitles, setJobTitles] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchQuestions();
    fetchJobTitles();
  }, []);

  useEffect(() => {
    filterQuestions();
  }, [questions, searchTerm, selectedType, selectedJobTitle]);

  const fetchQuestions = async () => {
    try {
      const response = await questionsApi.getAll({ limit: 1000 });
      setQuestions(response.data);
    } catch (error) {
      console.error('Failed to fetch questions:', error);
      toast.error('Failed to load questions');
    } finally {
      setLoading(false);
    }
  };

  const fetchJobTitles = async () => {
    try {
      const response = await questionsApi.getJobTitles();
      setJobTitles(response.data);
    } catch (error) {
      console.error('Failed to fetch job titles:', error);
    }
  };

  const filterQuestions = () => {
    let filtered = questions.filter(question => {
      const matchesSearch = question.question_text.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           question.job_title.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = selectedType === 'all' || question.question_type === selectedType;
      const matchesJob = selectedJobTitle === 'all' || question.job_title === selectedJobTitle;
      
      return matchesSearch && matchesType && matchesJob;
    });
    setFilteredQuestions(filtered);
  };

  const toggleFlag = async (questionId: number) => {
    try {
      const question = questions.find(q => q.id === questionId);
      if (!question) return;

      await questionsApi.update(questionId, {
        is_flagged: !question.is_flagged
      });
      
      setQuestions(prev => 
        prev.map(q => 
          q.id === questionId 
            ? { ...q, is_flagged: !q.is_flagged }
            : q
        )
      );
      
      toast.success(question.is_flagged ? 'Question unflagged' : 'Question flagged');
    } catch (error) {
      toast.error('Failed to update question');
      console.error('Failed to toggle flag:', error);
    }
  };

  const updateDifficulty = async (questionId: number, newDifficulty: number) => {
    try {
      await questionsApi.update(questionId, {
        difficulty: newDifficulty
      });
      
      setQuestions(prev => 
        prev.map(q => 
          q.id === questionId 
            ? { ...q, difficulty: newDifficulty }
            : q
        )
      );
      
      toast.success('Difficulty updated');
    } catch (error) {
      toast.error('Failed to update difficulty');
      console.error('Failed to update difficulty:', error);
    }
  };

  const deleteQuestion = async (questionId: number) => {
    if (!window.confirm('Are you sure you want to delete this question?')) return;
    
    try {
      await questionsApi.delete(questionId);
      setQuestions(prev => prev.filter(q => q.id !== questionId));
      toast.success('Question deleted');
    } catch (error) {
      toast.error('Failed to delete question');
      console.error('Failed to delete question:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div 
        className="flex items-center justify-between"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div>
          <h1 className="text-4xl font-bold text-gray-900">Question Library</h1>
          <p className="text-gray-600 mt-2">Manage and organize your interview questions</p>
        </div>
        
        <motion.button
          onClick={() => setShowFilters(!showFilters)}
          className="md:hidden flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors duration-200"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <SlidersHorizontal className="w-4 h-4" />
          <span>Filters</span>
        </motion.button>
      </motion.div>

      {/* Filters */}
      <motion.div 
        className={`bg-white rounded-2xl border border-gray-200 p-6 shadow-soft ${showFilters ? 'block' : 'hidden md:block'}`}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
      >
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search questions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200 bg-gray-50 focus:bg-white"
            />
          </div>

          {/* Type Filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200 bg-gray-50 focus:bg-white"
          >
            <option value="all">All Types</option>
            <option value="technical">Technical</option>
            <option value="behavioral">Behavioral</option>
          </select>

          {/* Job Title Filter */}
          <select
            value={selectedJobTitle}
            onChange={(e) => setSelectedJobTitle(e.target.value)}
            className="px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200 bg-gray-50 focus:bg-white"
          >
            <option value="all">All Job Titles</option>
            {jobTitles.map(title => (
              <option key={title} value={title}>{title}</option>
            ))}
          </select>

          {/* Results Count */}
          <div className="flex items-center justify-center md:justify-start text-sm text-gray-600 bg-gray-50 rounded-xl px-4 py-3 border border-gray-200">
            <Filter className="w-4 h-4 mr-2" />
            <span className="font-medium">{filteredQuestions.length}</span>
            <span className="mx-1">of</span>
            <span className="font-medium">{questions.length}</span>
            <span className="ml-1">questions</span>
          </div>
        </div>
      </motion.div>

      {/* Questions List */}
      <div className="space-y-4">
        {filteredQuestions.length === 0 ? (
          <motion.div 
            className="text-center py-16 bg-white rounded-2xl border border-gray-200 shadow-soft"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <MessageSquare className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No questions found</h3>
            <p className="text-gray-600">Try adjusting your filters or generate some new questions</p>
          </motion.div>
        ) : (
          filteredQuestions.map((question, index) => (
            <QuestionCard
              key={question.id}
              question={question}
              onToggleFlag={toggleFlag}
              onUpdateDifficulty={updateDifficulty}
              onDelete={deleteQuestion}
              index={index}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default Questions;