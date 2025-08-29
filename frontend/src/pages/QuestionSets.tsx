import React, { useState, useEffect } from "react";
import { fetchQuestionSets } from "../services/api";
import QuestionSetCard from "../components/QuestionSetCard";
import LoadingSpinner from "../components/LoadingSpinner";
import { QuestionSet } from "../types";

const QuestionSets: React.FC = () => {
  const [questionSets, setQuestionSets] = useState<QuestionSet[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadQuestionSets = async () => {
      try {
        setLoading(true);
        const data = await fetchQuestionSets();
        setQuestionSets(data);
        setError(null);
      } catch (err) {
        setError("Failed to load question sets. Please try again.");
        console.error("Error fetching question sets:", err);
      } finally {
        setLoading(false);
      }
    };

    loadQuestionSets();
  }, []);

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
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mt-4">
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Question Sets</h1>

      {questionSets.length === 0 ? (
        <p className="text-gray-600">
          No question sets found. Create one from the Questions page.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {questionSets.map((set) => (
            <QuestionSetCard
              key={set.id}
              id={set.id}
              name={set.name}
              description={set.description || ""}
              jobTitle={set.job_title}
              questionCount={getQuestionCount(set.question_ids)}
              onSelect={() => console.log(`Selected set ${set.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default QuestionSets;
