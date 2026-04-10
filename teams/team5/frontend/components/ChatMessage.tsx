"use client";

import React from "react";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

interface ChatMessageProps {
  message: ChatMessageType;
  sessionId: string;
  query?: string;
}

function renderMarkdown(text: string): string {
  // Lightweight markdown-to-HTML for hackathon speed
  let html = text
    // Escape HTML entities first
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    // Bold
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    // Italic
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    // Links [text](url)
    .replace(
      /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-teal-700 underline hover:text-teal-900">$1</a>'
    )
    // Line breaks
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br/>");
  // Wrap in paragraph
  html = `<p>${html}</p>`;
  // Clean up empty paragraphs
  html = html.replace(/<p><\/p>/g, "");
  return html;
}

export default function ChatMessage({
  message,
  sessionId,
  query,
}: ChatMessageProps) {
  const isUser = message.role === "user";

  // Suppress unused variable warnings — these will be used by Task 14 components
  void sessionId;
  void query;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] ${
          isUser
            ? "bg-teal-700 text-white rounded-2xl rounded-br-md px-4 py-3"
            : "bg-white border border-gray-200 rounded-2xl rounded-bl-md px-5 py-4 shadow-sm"
        }`}
      >
        {/* Message content */}
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        ) : (
          <>
            <div
              className="text-sm leading-relaxed prose prose-sm max-w-none prose-a:text-teal-700 prose-a:no-underline hover:prose-a:underline"
              dangerouslySetInnerHTML={{
                __html: renderMarkdown(message.content),
              }}
            />

            {/* Inline charts — placeholder for DataChart (Task 14) */}
            {message.chartData && message.chartData.length > 0 && (
              <div className="mt-3 space-y-3">
                {message.chartData.map((chart, idx) => (
                  <div
                    key={idx}
                    className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-xs text-gray-500"
                  >
                    <span className="font-medium text-gray-700">
                      {chart.title}
                    </span>{" "}
                    — grafiek wordt geladen (DataChart component volgt in Task
                    14)
                  </div>
                ))}
              </div>
            )}

            {/* Source cards — placeholder for SourceCard (Task 14) */}
            {message.sourceCards && message.sourceCards.length > 0 && (
              <div className="mt-3 border-t border-gray-100 pt-3">
                <p className="text-xs font-medium text-gray-500 mb-2">
                  Bronnen:
                </p>
                <div className="flex flex-wrap gap-2">
                  {message.sourceCards.map((source, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-3 py-1 text-xs text-teal-800 border border-teal-200"
                    >
                      {source.source}
                      {source.contributed && (
                        <span className="text-teal-600" title="Heeft bijgedragen">
                          *
                        </span>
                      )}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Feedback widget placeholder (Task 14) */}
            {message.id && message.id !== "welcome" && (
              <div className="mt-2 border-t border-gray-100 pt-2 flex items-center gap-2">
                <span className="text-xs text-gray-400">
                  Was dit antwoord nuttig?
                </span>
                <button
                  className="text-gray-400 hover:text-teal-600 transition-colors"
                  title="Positief"
                  aria-label="Positieve feedback"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3H14z"
                    />
                  </svg>
                </button>
                <button
                  className="text-gray-400 hover:text-red-500 transition-colors"
                  title="Negatief"
                  aria-label="Negatieve feedback"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3H10z"
                    />
                  </svg>
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
