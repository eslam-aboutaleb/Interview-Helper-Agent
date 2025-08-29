import React from "react";

interface QuestionSetCardProps {
  id: number;
  name: string;
  description: string;
  jobTitle: string;
  questionCount: number;
  onSelect?: () => void;
}

const QuestionSetCard: React.FC<QuestionSetCardProps> = ({
  id,
  name,
  description,
  jobTitle,
  questionCount,
  onSelect,
}) => {
  return (
    <div className="bg-white shadow-md rounded-lg p-4 hover:shadow-lg transition-shadow">
      <h3 className="text-lg font-semibold">{name}</h3>
      <p className="text-sm text-gray-600 mt-1">{jobTitle}</p>
      <p className="mt-2 text-gray-700">{description}</p>
      <div className="flex justify-between items-center mt-4">
        <span className="text-sm text-gray-500">{questionCount} questions</span>
        {onSelect && (
          <button
            onClick={onSelect}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            View
          </button>
        )}
      </div>
    </div>
  );
};

export default QuestionSetCard;
