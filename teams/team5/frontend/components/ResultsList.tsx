"use client";

import React from "react";

interface ResultsListProps {
  content: string;
  onMoreInfo: () => void;
  onNewTopic: () => void;
}

export default function ResultsList({
  content,
  onMoreInfo,
  onNewTopic,
}: ResultsListProps) {
  const renderContent = (text: string) => {
    const lines = text.split("\n");
    return lines.map((line, i) => {
      const withLinks = line.replace(
        /\[([^\]]+)\]\(([^)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-teal-700 underline hover:text-teal-900">$1</a>'
      );
      const withBold = withLinks.replace(
        /\*\*([^*]+)\*\*/g,
        "<strong>$1</strong>"
      );
      return (
        <p
          key={i}
          className={`${line.trim() === "" ? "h-3" : ""}`}
          dangerouslySetInnerHTML={{ __html: withBold }}
        />
      );
    });
  };

  return (
    <div>
      <div className="prose prose-sm max-w-none text-gray-800 space-y-1">
        {renderContent(content)}
      </div>

      <div className="mt-6 flex gap-3">
        <button
          onClick={onMoreInfo}
          className="px-4 py-2.5 text-sm font-medium rounded-xl border border-teal-300 bg-teal-50 text-teal-800 hover:bg-teal-100 transition-colors"
        >
          Meer informatie
        </button>
        <button
          onClick={onNewTopic}
          className="px-4 py-2.5 text-sm font-medium rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Nieuw onderwerp
        </button>
      </div>
    </div>
  );
}
