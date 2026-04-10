"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import type {
  ChatMessage as ChatMessageType,
  UserProfile,
  SourceCard,
  ChartData,
} from "@/lib/types";
import { sendChatMessage } from "@/lib/chat-client";
import ChatMessage from "@/components/ChatMessage";
import ProfileSelector from "@/components/ProfileSelector";

function generateId(): string {
  return crypto.randomUUID();
}

const WELCOME_MESSAGE: ChatMessageType = {
  role: "assistant",
  content:
    "Welkom bij de IKNL Kankerinformatie Chat! Ik help u graag met betrouwbare informatie over kanker uit vertrouwde bronnen zoals kanker.nl, NKR-Cijfers en de Kankeratlas.\n\nKies eerst uw profiel in het menu links, of stel direct uw vraag. Ik pas mijn antwoorden aan op basis van uw profiel.\n\n**Voorbeeldvragen:**\n- Wat is borstkanker en hoe wordt het behandeld?\n- Hoe vaak komt longkanker voor bij mannen?\n- Wat zijn de overlevingscijfers voor darmkanker?\n- Is er een hoger risico op kanker in mijn regio?",
  id: "welcome",
};

const PROFILE_OPTIONS: { value: UserProfile; label: string; description: string; icon: string }[] = [
  {
    value: "patient",
    label: "Patient / naaste",
    description: "Begrijpelijke taal, gericht op persoonlijke situatie",
    icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z",
  },
  {
    value: "professional",
    label: "Zorgprofessional",
    description: "Medische terminologie, evidence-based informatie",
    icon: "M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5",
  },
  {
    value: "policymaker",
    label: "Beleidsmaker",
    description: "Cijfers, trends en regionale vergelijkingen",
    icon: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z",
  },
];

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessageType[]>([
    WELCOME_MESSAGE,
  ]);
  const [currentProfile, setCurrentProfile] =
    useState<UserProfile>("patient");
  const [inputText, setInputText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId] = useState("pending");
  // Set session ID only on client to avoid hydration mismatch
  const sessionIdRef = useRef<string>("");
  if (sessionIdRef.current === "" && typeof window !== "undefined") {
    sessionIdRef.current = generateId();
  }
  const currentSessionId = sessionIdRef.current || sessionId;
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleProfileChange = (profile: UserProfile) => {
    setCurrentProfile(profile);
    const profileLabels: Record<UserProfile, string> = {
      patient: "Patient / naaste",
      professional: "Zorgprofessional",
      policymaker: "Beleidsmaker",
    };
    const notification: ChatMessageType = {
      role: "assistant",
      content: `Profiel gewijzigd naar **${profileLabels[profile]}**. Mijn antwoorden worden nu hierop aangepast.`,
      id: generateId(),
    };
    setMessages((prev) => [...prev, notification]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || isStreaming) return;

    const userMessage: ChatMessageType = {
      role: "user",
      content: text,
      id: generateId(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText("");
    setIsStreaming(true);

    // Build history from existing messages (exclude welcome and notifications without sourceCards)
    const history = messages
      .filter((m) => m.id !== "welcome")
      .map((m) => ({ role: m.role, content: m.content }));

    const assistantMessageId = generateId();
    const assistantMessage: ChatMessageType = {
      role: "assistant",
      content: "",
      id: assistantMessageId,
      sourceCards: [],
      chartData: [],
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      const stream = sendChatMessage({
        message: text,
        session_id: currentSessionId,
        profile: currentProfile,
        history,
      });

      for await (const event of stream) {
        switch (event.event) {
          case "token": {
            const tokenText = (event.data as { text: string }).text;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId
                  ? { ...m, content: m.content + tokenText }
                  : m
              )
            );
            break;
          }
          case "source_card": {
            const card = event.data as unknown as SourceCard;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId
                  ? {
                      ...m,
                      sourceCards: [...(m.sourceCards || []), card],
                    }
                  : m
              )
            );
            break;
          }
          case "chart_data": {
            const chart = event.data as unknown as ChartData;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId
                  ? {
                      ...m,
                      chartData: [...(m.chartData || []), chart],
                    }
                  : m
              )
            );
            break;
          }
          case "done":
            // Stream complete
            break;
          case "error": {
            const errMsg = (event.data as { message: string }).message;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId
                  ? {
                      ...m,
                      content:
                        m.content +
                        `\n\nEr is een fout opgetreden: ${errMsg}`,
                    }
                  : m
              )
            );
            break;
          }
        }
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? {
                ...m,
                content:
                  "Er is een verbindingsfout opgetreden. Probeer het opnieuw.",
              }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? "w-72" : "w-0"
        } transition-all duration-300 overflow-hidden bg-white border-r border-gray-200 flex flex-col`}
      >
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-teal-700 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm font-bold">IK</span>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-gray-900">
                IKNL KankerChat
              </h1>
              <p className="text-xs text-gray-500">
                Betrouwbare kankerinformatie
              </p>
            </div>
          </div>
        </div>

        {/* Inline ProfileSelector — will be replaced by dedicated component in Task 14 */}
        <div className="p-4 flex-1">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Uw profiel
          </p>
          <div className="space-y-2">
            {PROFILE_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => handleProfileChange(option.value)}
                className={`w-full text-left px-3 py-2.5 rounded-lg border transition-colors ${
                  currentProfile === option.value
                    ? "bg-teal-50 border-teal-300 text-teal-800"
                    : "bg-white border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <svg
                    className={`w-5 h-5 shrink-0 ${
                      currentProfile === option.value
                        ? "text-teal-600"
                        : "text-gray-400"
                    }`}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.5}
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d={option.icon}
                    />
                  </svg>
                  <div>
                    <p className="text-sm font-medium">{option.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {option.description}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 border-t border-gray-200">
          <p className="text-xs text-gray-400 leading-relaxed">
            Deze chat is een prototype en geeft geen persoonlijk medisch
            advies. Raadpleeg altijd uw arts of specialist.
          </p>
        </div>
      </aside>

      {/* Main chat area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 bg-white border-b border-gray-200 flex items-center px-4 gap-3 shrink-0">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-md hover:bg-gray-100 text-gray-500"
            aria-label="Toggle sidebar"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
          <span className="text-sm text-gray-600">
            Sessie: {currentSessionId.slice(0, 8)}...
          </span>
          {isStreaming && (
            <span className="ml-auto text-xs text-teal-700 flex items-center gap-1">
              <span className="w-2 h-2 bg-teal-600 rounded-full animate-pulse" />
              Antwoord wordt opgesteld...
            </span>
          )}
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto">
            {messages.map((msg, idx) => (
              <ChatMessage
                key={msg.id || idx}
                message={msg}
                sessionId={currentSessionId}
                query={
                  msg.role === "assistant" && idx > 0
                    ? messages
                        .slice(0, idx)
                        .filter((m) => m.role === "user")
                        .pop()?.content
                    : undefined
                }
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 bg-white p-4 shrink-0">
          <form
            onSubmit={handleSubmit}
            className="max-w-3xl mx-auto flex gap-3"
          >
            <textarea
              ref={inputRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Stel uw vraag over kanker..."
              rows={1}
              disabled={isStreaming}
              className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={isStreaming || !inputText.trim()}
              className="px-5 py-3 bg-teal-700 text-white text-sm font-medium rounded-xl hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isStreaming ? (
                <svg
                  className="w-5 h-5 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
              ) : (
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              )}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
