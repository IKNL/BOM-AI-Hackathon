// frontend/components/FeedbackWidget.tsx

"use client";

import React, { useState } from "react";
import { submitFeedback } from "@/lib/chat-client";
import type { FeedbackCategory } from "@/lib/types";

interface FeedbackWidgetProps {
  sessionId: string;
  messageId: string;
  query: string;
  sourcesTried: string[];
}

const CATEGORY_OPTIONS: { value: FeedbackCategory; label: string }[] = [
  {
    value: "intent",
    label: "U heeft mijn vraag verkeerd begrepen",
  },
  {
    value: "execution",
    label: "De juiste vraag, maar op de verkeerde plek gezocht",
  },
  {
    value: "info",
    label: "De informatie zelf klopt niet",
  },
];

export default function FeedbackWidget({
  sessionId,
  messageId,
  query,
  sourcesTried,
}: FeedbackWidgetProps) {
  const [rating, setRating] = useState<"positive" | "negative" | null>(null);
  const [showPanel, setShowPanel] = useState(false);
  const [category, setCategory] = useState<FeedbackCategory | null>(null);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleThumbsUp = async () => {
    setRating("positive");
    setError(null);
    try {
      await submitFeedback({
        session_id: sessionId,
        message_id: messageId,
        rating: "positive",
        query,
        sources_tried: sourcesTried,
      });
      setSubmitted(true);
    } catch {
      setError("Versturen mislukt, probeer opnieuw");
      setRating(null); // let them retry
    }
  };

  const handleThumbsDown = () => {
    setRating("negative");
    setShowPanel(true);
  };

  const handleSubmitNegative = async () => {
    if (!category) return;
    setError(null);
    try {
      await submitFeedback({
        session_id: sessionId,
        message_id: messageId,
        rating: "negative",
        category,
        comment: comment.trim() || undefined,
        query,
        sources_tried: sourcesTried,
      });
      setSubmitted(true);
    } catch {
      setError("Versturen mislukt, probeer opnieuw");
      // Keep the panel open so they can retry
    }
  };

  const handleCancel = () => {
    setRating(null);
    setShowPanel(false);
    setCategory(null);
    setComment("");
    setError(null);
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleThumbsUp}
          disabled={rating !== null}
          className={`p-1 rounded transition-colors ${
            rating === "positive"
              ? "text-green-600"
              : "text-gray-300 hover:text-gray-500"
          } disabled:cursor-default`}
          aria-label="Positieve feedback"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
          </svg>
        </button>

        <button
          type="button"
          onClick={handleThumbsDown}
          disabled={rating !== null}
          className={`p-1 rounded transition-colors ${
            rating === "negative"
              ? "text-red-500"
              : "text-gray-300 hover:text-gray-500"
          } disabled:cursor-default`}
          aria-label="Negatieve feedback"
        >
          <svg
            className="w-4 h-4 rotate-180"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
          </svg>
        </button>

        {submitted && (
          <span className="text-xs text-green-600 ml-1">
            Bedankt voor uw feedback!
          </span>
        )}
        {error && !showPanel && (
          <span className="text-xs text-red-600 ml-1">{error}</span>
        )}
      </div>

      {showPanel && !submitted && (
        <div
          role="group"
          aria-labelledby="feedback-panel-heading"
          className="flex flex-col gap-2 p-3 bg-gray-50 border border-gray-200 rounded-lg"
        >
          <p id="feedback-panel-heading" className="text-xs font-medium text-gray-700">
            Wat ging er mis?
          </p>
          <div role="radiogroup" aria-labelledby="feedback-panel-heading" className="flex flex-wrap gap-2">
            {CATEGORY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                role="radio"
                aria-checked={category === opt.value}
                onClick={() => setCategory(opt.value)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                  category === opt.value
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-700 border-gray-300 hover:border-gray-400"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Kunt u dit toelichten? (optioneel)"
            rows={2}
            className="text-xs px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
          />
          {error && (
            <span className="text-xs text-red-600">{error}</span>
          )}
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={handleCancel}
              className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
            >
              Annuleer
            </button>
            <button
              type="button"
              onClick={handleSubmitNegative}
              disabled={!category}
              className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Verstuur
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
