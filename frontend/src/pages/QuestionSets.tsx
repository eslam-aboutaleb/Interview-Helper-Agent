import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { FolderOpen, Plus } from "lucide-react";
import { fetchQuestionSets, parseAxiosError } from "../services/api";
import { ErrorResponse, ErrorType } from '../services/errorHandler';
import QuestionSetCard from "../components/QuestionSetCard";
import LoadingSpinner from "../components/LoadingSpinner";
import Alert from "../components/Alert";
import EmptyState from "../components/EmptyState";
import { QuestionSet } from "../types";

const QuestionSets: React.FC = () => {
  const [questionSets, setQuestionSets] = useState<QuestionSet[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<ErrorResponse | null>(null);

  useEffect(() => {
    loadQuestionSets();
  }, []);

  const loadQuestionSets = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchQuestionSets();
      setQuestionSets(data);
    } catch (err) {
      const parsedError = parseAxiosError(err);
      setError(parsedError);
      console.error("Error fetching question sets:", parsedError);
    } finally {
      setLoading(false);
    }
  };

  // Calculate question count from the question_ids field
  const getQuestionCount = (questionIds: string): number => {
    try {
      // The question_ids could be a JSON string array or a comma-separated string
      if (questionIds.startsWith("[")) {
        // If it's a JSON string
        return JSON.parse(questionIds).length;
      } else {
        // If it's a comma-separated string
        return questionIds.split(",").filter((id) => id.trim() !== "").length;
      }
    } catch (e) {
      console.error("Error parsing question_ids:", e);
      return 0;
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        title="Failed to Load Question Sets"
        message={error.message}
        details={error.details}
        actionLabel="Retry"
        onAction={loadQuestionSets}
        onDismiss={() => setError(null)}
      />
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
          <h1 className="text-4xl font-bold text-gray-900">Question Sets</h1>
          <p className="text-gray-600 mt-2">Create and organize themed question collections</p>
        </div>
        
        <motion.button
          onClick={() => window.location.href = '/questions'}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors duration-200"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Plus className="w-4 h-4" />
          <span>Create Set</span>
        </motion.button>
      </motion.div>

      {questionSets.length === 0 ? (
        <EmptyState
          title="No question sets yet"
          message="Create your first question set to organize and practice specific interview topics."
          icon={<FolderOpen className="w-12 h-12 text-gray-400" />}
          actionLabel="Create Question Set"
          onAction={() => window.location.href = '/questions'}
        />
      ) : (
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          {questionSets.map((set, index) => (
            <motion.div
              key={set.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              <QuestionSetCard
                id={set.id}
                name={set.name}
                description={set.description || ""}
                jobTitle={set.job_title}
                questionCount={getQuestionCount(set.question_ids)}
                onSelect={() => console.log(`Selected set ${set.id}`)}
              />
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
};

export default QuestionSets;
