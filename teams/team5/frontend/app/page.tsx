"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import type {
  ChatMessage as ChatMessageType,
  SourceCard,
  IntakeState,
  AiBekendheid,
  GebruikerType,
  GegevensModel,
} from "@/lib/types";
import { summarizeQuestion, searchAndStream } from "@/lib/intake-client";
import ChatMessage from "@/components/ChatMessage";
import IntakeButtons from "@/components/IntakeButtons";
import ResultsList from "@/components/ResultsList";

function generateId(): string {
  return crypto.randomUUID();
}

const BEKENDHEID_OPTIONS = [
  { value: "niet_bekend", label: "Niet bekend" },
  { value: "enigszins", label: "Enigszins bekend" },
  { value: "erg_bekend", label: "Erg bekend" },
];

const GEBRUIKER_OPTIONS = [
  { value: "patient", label: "Ik ben patiënt of naaste" },
  { value: "publiek", label: "Ik ben algemeen publiek" },
  { value: "zorgverlener", label: "Ik ben een zorgverlener" },
  { value: "student", label: "Ik ben een student of docent" },
  { value: "beleidsmaker", label: "Ik ben een beleidsmaker" },
  { value: "onderzoeker", label: "Ik ben een onderzoeker of wetenschapper" },
  { value: "journalist", label: "Ik ben een journalist" },
  { value: "anders", label: "Anders" },
];

const GEBRUIKER_LABELS: Record<string, string> = {
  patient: "patiënt of naaste",
  publiek: "algemeen publiek",
  zorgverlener: "zorgverlener",
  student: "student of docent",
  beleidsmaker: "beleidsmaker",
  onderzoeker: "onderzoeker of wetenschapper",
  journalist: "journalist",
  anders: "anders",
};

const INITIAL_GEGEVENS: GegevensModel = {
  ai_bekendheid: null,
  gebruiker_type: null,
  vraag_tekst: null,
  kankersoort: null,
  vraag_type: null,
  samenvatting: null,
  bevestigd: false,
};

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [intakeState, setIntakeState] = useState<IntakeState>("INTAKE_START");
  const [gegevens, setGegevens] = useState<GegevensModel>(INITIAL_GEGEVENS);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [resultContent, setResultContent] = useState("");
  const [currentSessionId, setCurrentSessionId] = useState("pending");

  useEffect(() => {
    setCurrentSessionId(generateId());
  }, []);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, intakeState, resultContent, scrollToBottom]);

  const addBotMessage = useCallback((content: string) => {
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content, id: generateId() },
    ]);
  }, []);

  const addUserMessage = useCallback((content: string) => {
    setMessages((prev) => [
      ...prev,
      { role: "user", content, id: generateId() },
    ]);
  }, []);

  // Show initial welcome + first question on mount
  useEffect(() => {
    addBotMessage(
      "Welkom bij de IKNL Infobot! Ik help u betrouwbare kankerinformatie te vinden.\n\n" +
        "**Let op:** Dit is een prototype (BrabantHack_26). Dit is geen medisch hulpmiddel.\n\n" +
        "Laten we beginnen. **Hoe bekend bent u met het gebruiken van een AI-chatbot?**"
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- State machine handlers ---

  const handleBekendheid = (value: string) => {
    addUserMessage(
      BEKENDHEID_OPTIONS.find((o) => o.value === value)?.label || value
    );
    setGegevens((prev) => ({
      ...prev,
      ai_bekendheid: value as AiBekendheid,
    }));
    addBotMessage("**Wat is uw rol?**");
    setIntakeState("GEBRUIKER_TYPE");
  };

  const handleGebruikerType = (value: string) => {
    addUserMessage(
      GEBRUIKER_OPTIONS.find((o) => o.value === value)?.label || value
    );
    setGegevens((prev) => ({
      ...prev,
      gebruiker_type: value as GebruikerType,
    }));

    const prompt =
      gegevens.ai_bekendheid === "niet_bekend"
        ? "**Schrijf in één zin duidelijk uw vraag op.**"
        : "**Wat is uw vraag?**";
    addBotMessage(prompt);
    setIntakeState("VRAAG");
  };

  const handleVraagSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || isLoading) return;

    addUserMessage(text);
    setInputText("");
    setGegevens((prev) => ({ ...prev, vraag_tekst: text }));
    setIsLoading(true);

    try {
      const result = await summarizeQuestion(
        gegevens.gebruiker_type!,
        text
      );
      setGegevens((prev) => ({
        ...prev,
        samenvatting: result.samenvatting,
        kankersoort: result.kankersoort === "geen" ? null : result.kankersoort,
        vraag_type: result.vraag_type,
      }));

      const typeLabel = GEBRUIKER_LABELS[gegevens.gebruiker_type!] || gegevens.gebruiker_type;
      addBotMessage(
        `Als ik het goed begrijp is dit uw vraag:\n\n` +
          `> U bent een **${typeLabel}** en zoekt informatie over: *${result.samenvatting}*\n\n` +
          `**Klopt dit?**`
      );
      setIntakeState("SAMENVATTING");
    } catch {
      addBotMessage(
        "Er is een fout opgetreden bij het verwerken van uw vraag. Probeer het opnieuw."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async () => {
    setIntakeState("SEARCH");
    setIsLoading(true);
    setResultContent("");

    const resultMsgId = generateId();
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", id: resultMsgId, sourceCards: [] },
    ]);

    try {
      const stream = searchAndStream({
        ai_bekendheid: gegevens.ai_bekendheid!,
        gebruiker_type: gegevens.gebruiker_type!,
        vraag_tekst: gegevens.vraag_tekst!,
        kankersoort: gegevens.kankersoort,
        vraag_type: gegevens.vraag_type,
        samenvatting: gegevens.samenvatting!,
      });

      let fullText = "";

      for await (const event of stream) {
        switch (event.event) {
          case "token": {
            const tokenText = (event.data as { text: string }).text;
            fullText += tokenText;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === resultMsgId
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
                m.id === resultMsgId
                  ? { ...m, sourceCards: [...(m.sourceCards || []), card] }
                  : m
              )
            );
            break;
          }
          case "done":
            break;
          case "error": {
            const errMsg = (event.data as { message: string }).message;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === resultMsgId
                  ? { ...m, content: m.content + `\n\nFout: ${errMsg}` }
                  : m
              )
            );
            break;
          }
        }
      }

      setResultContent(fullText);
      setIntakeState("RESULTS");
    } catch {
      addBotMessage("Er is een verbindingsfout opgetreden. Probeer het opnieuw.");
      setIntakeState("SAMENVATTING");
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = (confirmed: boolean) => {
    if (confirmed) {
      addUserMessage("Ja, dit klopt");
      setGegevens((prev) => ({ ...prev, bevestigd: true }));
      handleSearch();
    } else {
      addUserMessage("Nee, ik wil iets aanpassen");
      addBotMessage("Geen probleem. **Wat is uw rol?**");
      setGegevens((prev) => ({
        ...prev,
        vraag_tekst: null,
        kankersoort: null,
        vraag_type: null,
        samenvatting: null,
        bevestigd: false,
      }));
      setIntakeState("GEBRUIKER_TYPE");
    }
  };

  const handleMoreInfo = () => {
    addBotMessage("Ik zoek aanvullende informatie voor u...");
    handleSearch();
  };

  const handleNewTopic = () => {
    addBotMessage(
      "Prima, laten we een nieuw onderwerp bespreken.\n\n**Wat is uw vraag?**"
    );
    setGegevens((prev) => ({
      ...prev,
      vraag_tekst: null,
      kankersoort: null,
      vraag_type: null,
      samenvatting: null,
      bevestigd: false,
    }));
    setResultContent("");
    setIntakeState("VRAAG");
  };

  const handleFollowUpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || isLoading) return;

    addUserMessage(text);
    setInputText("");
    setIsLoading(true);

    try {
      const result = await summarizeQuestion(gegevens.gebruiker_type!, text);
      setGegevens((prev) => ({
        ...prev,
        vraag_tekst: text,
        samenvatting: result.samenvatting,
        kankersoort: result.kankersoort === "geen" ? null : result.kankersoort,
        vraag_type: result.vraag_type,
        bevestigd: false,
      }));
      const typeLabel =
        GEBRUIKER_LABELS[gegevens.gebruiker_type!] || gegevens.gebruiker_type;
      addBotMessage(
        `Als ik het goed begrijp is dit uw vraag:\n\n` +
          `> U bent een **${typeLabel}** en zoekt informatie over: *${result.samenvatting}*\n\n` +
          `**Klopt dit?**`
      );
      setIntakeState("SAMENVATTING");
    } catch {
      addBotMessage("Er is een fout opgetreden. Probeer het opnieuw.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (intakeState === "VRAAG") {
        handleVraagSubmit(e);
      } else if (intakeState === "RESULTS") {
        handleFollowUpSubmit(e);
      }
    }
  };

  // --- Render ---

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className="w-72 bg-white border-r border-gray-200 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-teal-700 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm font-bold">IK</span>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-gray-900">
                IKNL Infobot
              </h1>
              <p className="text-xs text-gray-500">
                Betrouwbare kankerinformatie
              </p>
            </div>
          </div>
        </div>

        {/* Progress indicator */}
        <div className="p-4 flex-1">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Voortgang
          </p>
          <div className="space-y-2">
            {[
              { state: "INTAKE_START", label: "AI-bekendheid" },
              { state: "GEBRUIKER_TYPE", label: "Type gebruiker" },
              { state: "VRAAG", label: "Uw vraag" },
              { state: "SAMENVATTING", label: "Bevestiging" },
              { state: "RESULTS", label: "Resultaten" },
            ].map((step, idx) => {
              const states: IntakeState[] = [
                "INTAKE_START",
                "GEBRUIKER_TYPE",
                "VRAAG",
                "SAMENVATTING",
                "RESULTS",
              ];
              const currentIdx = states.indexOf(intakeState);
              const stepIdx = states.indexOf(step.state as IntakeState);
              const adjustedCurrentIdx =
                intakeState === "SEARCH" ? states.indexOf("SAMENVATTING") + 0.5 : currentIdx;
              const isComplete = stepIdx < adjustedCurrentIdx;
              const isCurrent =
                step.state === intakeState ||
                (intakeState === "SEARCH" && step.state === "RESULTS");

              return (
                <div key={step.state} className="flex items-center gap-2">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium shrink-0 ${
                      isComplete
                        ? "bg-teal-600 text-white"
                        : isCurrent
                        ? "bg-teal-100 text-teal-700 border-2 border-teal-400"
                        : "bg-gray-100 text-gray-400"
                    }`}
                  >
                    {isComplete ? (
                      <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : (
                      idx + 1
                    )}
                  </div>
                  <span
                    className={`text-sm ${
                      isComplete
                        ? "text-teal-700 font-medium"
                        : isCurrent
                        ? "text-gray-900 font-medium"
                        : "text-gray-400"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
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
          <span className="text-sm text-gray-600">
            Sessie: {currentSessionId.slice(0, 8)}...
          </span>
          {isLoading && (
            <span className="ml-auto text-xs text-teal-700 flex items-center gap-1">
              <span className="w-2 h-2 bg-teal-600 rounded-full animate-pulse" />
              {intakeState === "SEARCH"
                ? "Bronnen worden doorzocht..."
                : "Wordt verwerkt..."}
            </span>
          )}
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto space-y-4">
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

            {/* Interactive elements based on current state */}
            {intakeState === "INTAKE_START" && !isLoading && (
              <div className="ml-10">
                <IntakeButtons
                  options={BEKENDHEID_OPTIONS}
                  onSelect={handleBekendheid}
                />
              </div>
            )}

            {intakeState === "GEBRUIKER_TYPE" && !isLoading && (
              <div className="ml-10">
                <IntakeButtons
                  options={GEBRUIKER_OPTIONS}
                  onSelect={handleGebruikerType}
                  columns={2}
                />
              </div>
            )}

            {intakeState === "SAMENVATTING" && !isLoading && (
              <div className="ml-10">
                <IntakeButtons
                  options={[
                    { value: "ja", label: "Ja, dit klopt" },
                    { value: "nee", label: "Nee, ik wil iets aanpassen" },
                  ]}
                  onSelect={(v) => handleConfirm(v === "ja")}
                />
              </div>
            )}

            {intakeState === "RESULTS" && !isLoading && (
              <div className="ml-10">
                <ResultsList
                  content=""
                  onMoreInfo={handleMoreInfo}
                  onNewTopic={handleNewTopic}
                />
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input area — only shown during VRAAG state or RESULTS (for follow-up) */}
        {(intakeState === "VRAAG" || intakeState === "RESULTS") && (
          <div className="border-t border-gray-200 bg-white p-4 shrink-0">
            <form
              onSubmit={intakeState === "VRAAG" ? handleVraagSubmit : handleFollowUpSubmit}
              className="max-w-3xl mx-auto flex gap-3"
            >
              <textarea
                ref={inputRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  intakeState === "VRAAG"
                    ? gegevens.ai_bekendheid === "niet_bekend"
                      ? "Schrijf in één zin duidelijk uw vraag..."
                      : "Stel uw vraag over kanker..."
                    : "Stel een nieuwe vraag..."
                }
                rows={1}
                disabled={isLoading}
                className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={isLoading || !inputText.trim()}
                className="px-5 py-3 bg-teal-700 text-white text-sm font-medium rounded-xl hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
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
        )}
      </main>
    </div>
  );
}
