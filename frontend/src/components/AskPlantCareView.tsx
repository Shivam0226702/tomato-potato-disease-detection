import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  Send,
  Sprout,
  User,
  BookOpen,
  Sparkles,
  AlertCircle,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';
import type { DiagnosisResult, QueryResponse } from '../types';
import { queryPlantCare, fetchAiStatus } from '../services/api';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  crop?: string;
  disease?: string;
  sources?: string[];
  disclaimer?: string;
  is_ai?: boolean;
  model?: string;
  error?: string;
}

interface AskPlantCareViewProps {
  currentAnalysis: DiagnosisResult | null;
}

const SAMPLE_PROMPTS = [
  'What fungicide should I use for Early Blight?',
  'How often should I spray copper fungicide?',
  'How to prevent Late Blight spread during rainy weather?',
  'What are the early symptoms of potato late blight?',
  'Is it safe to eat potatoes with early blight?',
  'How can I control blight organically without chemicals?',
];

/**
 * Lightweight, safe markdown formatter for assistant responses.
 * Renders bold, headers, bullet points, callout blockquotes, and code tags cleanly.
 */
function FormattedAssistantMessage({ content }: { content: string }) {
  const lines = content.split('\n');

  // Helper to format inline elements (bold and code)
  const renderInline = (str: string) => {
    // Split by bold (**text**) and code (`text`)
    const parts = str.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-slate-900">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code
            key={i}
            className="px-1 py-0.5 rounded bg-slate-200/70 font-mono text-[11px] text-slate-800"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  return (
    <div className="space-y-2 text-xs leading-relaxed text-slate-800">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} className="h-1.5" />;
        }

        // Section Headers: ### Header or #### Header
        if (trimmed.startsWith('### ') || trimmed.startsWith('#### ')) {
          const headerText = trimmed.replace(/^#+\s*/, '');
          return (
            <h4
              key={idx}
              className="text-xs font-bold text-slate-900 pt-2 pb-0.5 uppercase tracking-wider flex items-center gap-1.5"
            >
              <span>{headerText}</span>
            </h4>
          );
        }

        // Blockquotes / Callout notes: > Note
        if (trimmed.startsWith('> ')) {
          const quoteText = trimmed.replace(/^>\s*/, '');
          return (
            <div
              key={idx}
              className="p-3 my-1 rounded-xl bg-teal-50/70 border border-teal-200/80 text-[11px] text-teal-900 leading-normal"
            >
              {renderInline(quoteText)}
            </div>
          );
        }

        // Bullet lists: - item or * item
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          const itemText = trimmed.slice(2);
          return (
            <div key={idx} className="flex items-start gap-2 pl-1 my-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-500 flex-shrink-0 mt-1.5" />
              <span>{renderInline(itemText)}</span>
            </div>
          );
        }

        // Horizontal rules: ---
        if (trimmed === '---') {
          return <hr key={idx} className="my-2 border-slate-200" />;
        }

        // Default paragraph line
        return <p key={idx}>{renderInline(trimmed)}</p>;
      })}
    </div>
  );
}

export const AskPlantCareView: React.FC<AskPlantCareViewProps> = ({ currentAnalysis }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text:
        'Hello! I am your PlantCare Agricultural Assistant, powered by Google Gemini. Ask me anything about managing Tomato and Potato diseases, spray intervals, organic cultural methods, soil hygiene, and weather safeguards.',
      timestamp: 'Just now',
      crop: 'Tomato & Potato',
      disease: 'Early Blight & Late Blight',
      is_ai: true,
      model: 'Gemini 3.5 Flash',
    },
  ]);
  const [inputValue, setInputValue] = useState<string>('');
  const [lastQuestion, setLastQuestion] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [useContext, setUseContext] = useState<boolean>(!!currentAnalysis);
  const [aiStatus, setAiStatus] = useState<{
    is_configured: boolean;
    model: string;
    has_sdk: boolean;
  } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Check Gemini connection on mount
  useEffect(() => {
    fetchAiStatus()
      .then((status) => setAiStatus(status))
      .catch(() =>
        setAiStatus({ is_configured: false, model: 'gemini-2.5-flash', has_sdk: true })
      );
  }, []);

  const handleSend = async (questionText?: string) => {
    const q = (questionText || inputValue).trim();
    if (!q || isLoading) return;

    if (q.length > 1000) {
      alert('Question exceeds the 1,000 character limit. Please shorten your question.');
      return;
    }

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setLastQuestion(q);
    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Build context if enabled
      const ctx =
        useContext && currentAnalysis
          ? {
              crop: currentAnalysis.crop,
              disease: currentAnalysis.disease,
              severity: currentAnalysis.severity.level,
              affected_percentage: currentAnalysis.severity.affected_percentage,
              confidence: currentAnalysis.confidence,
            }
          : undefined;

      // Build conversation history (excluding welcome message and error responses)
      const historyPayload = messages
        .filter((m) => m.id !== 'welcome' && !m.error)
        .slice(-6)
        .map((m) => ({
          role: m.sender === 'user' ? 'user' : 'assistant',
          text: m.text,
        }));

      const res: QueryResponse = await queryPlantCare(q, ctx, historyPayload);

      const assistantMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        sender: 'assistant',
        text: res.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        crop: res.crop,
        disease: res.disease,
        sources: res.sources,
        disclaimer: res.disclaimer,
        is_ai: res.is_ai,
        model: res.model,
        error: res.error,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const sanitizedErr = err.message || 'Unable to connect to server. Please check your network connection.';
      const errorMsg: ChatMessage = {
        id: `e-${Date.now()}`,
        sender: 'assistant',
        text: `Unable to process question: ${sanitizedErr}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        error: 'NETWORK_ERROR',
        is_ai: false,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="flex items-center justify-center gap-2 mb-2">
          {aiStatus?.is_configured ? (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 shadow-2xs">
              <Sparkles className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
              <span>Google Gemini AI Active • {aiStatus.model}</span>
            </div>
          ) : (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 shadow-2xs">
              <MessageSquare className="w-3.5 h-3.5 text-amber-600" />
              <span>Agronomic Knowledge Engine • Gemini Setup Available</span>
            </div>
          )}
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          Ask PlantCare
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Intelligent agronomic advice on spray schedules, fungicide active ingredients,
          weather safeguards, and organic cultural methods for Tomato and Potato crops.
        </p>
      </div>

      {/* Active Analysis Context Banner */}
      {currentAnalysis && (
        <div
          className={`p-4 rounded-2xl border transition-all ${
            useContext
              ? 'bg-emerald-50/80 border-emerald-300 text-emerald-950 shadow-2xs'
              : 'bg-slate-50 border-slate-200 text-slate-600'
          }`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span
                className={`w-3 h-3 rounded-full flex-shrink-0 ${
                  useContext ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'
                }`}
              />
              <div className="text-xs">
                <span className="font-bold">Active Diagnosis Context:</span>{' '}
                <span>
                  {currentAnalysis.crop} — {currentAnalysis.disease} ({currentAnalysis.severity.level}{' '}
                  Severity, {currentAnalysis.confidence.toFixed(1)}% Confidence)
                </span>
                <p className="text-[11px] opacity-80 mt-0.5">
                  {useContext
                    ? 'Questions will automatically incorporate this crop and pathogen context.'
                    : 'Context is currently disabled. Responses will be general.'}
                </p>
              </div>
            </div>

            <button
              onClick={() => setUseContext(!useContext)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors flex-shrink-0 cursor-pointer ${
                useContext
                  ? 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-2xs'
                  : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-100'
              }`}
            >
              {useContext ? 'Using Context' : 'Enable Context'}
            </button>
          </div>
        </div>
      )}

      {/* Sample Question Chips */}
      <div>
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
          Frequently Asked Questions:
        </span>
        <div className="flex flex-wrap gap-2">
          {SAMPLE_PROMPTS.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(prompt)}
              disabled={isLoading}
              className="px-3 py-1.5 rounded-full text-xs bg-white border border-slate-200 text-slate-700 hover:border-teal-500 hover:text-teal-700 hover:bg-teal-50/50 transition-all text-left shadow-2xs disabled:opacity-50 cursor-pointer"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Messages Stream */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 min-h-[420px] max-h-[600px] overflow-y-auto space-y-6">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-3 ${
              msg.sender === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {msg.sender === 'assistant' && (
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 shadow-xs ${
                  msg.is_ai ? 'bg-emerald-600 text-white' : 'bg-teal-600 text-white'
                }`}
              >
                {msg.is_ai ? <Sparkles className="w-4 h-4" /> : <Sprout className="w-4 h-4" />}
              </div>
            )}

            <div
              className={`max-w-2xl rounded-2xl p-4 text-xs leading-relaxed space-y-2.5 shadow-2xs ${
                msg.sender === 'user'
                  ? 'bg-emerald-600 text-white rounded-tr-xs'
                  : msg.error
                  ? 'bg-amber-50/80 border border-amber-300 text-slate-800 rounded-tl-xs'
                  : 'bg-slate-50 border border-slate-200/70 text-slate-800 rounded-tl-xs'
              }`}
            >
              {/* Header Badges on Assistant Messages */}
              {msg.sender === 'assistant' && (
                <div className="flex items-center justify-between pb-1 border-b border-slate-200/60">
                  <div className="flex items-center gap-1.5">
                    {msg.is_ai && !msg.error ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-100 text-emerald-800">
                        <Sparkles className="w-2.5 h-2.5 text-emerald-600" />
                        <span>Google Gemini AI</span>
                        {msg.model && <span className="opacity-70">({msg.model})</span>}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-200 text-slate-700">
                        <Sprout className="w-2.5 h-2.5 text-teal-600" />
                        <span>{msg.error ? 'System Notice' : 'Agronomic Knowledge Base'}</span>
                      </span>
                    )}
                    {msg.crop && msg.crop !== 'Tomato & Potato' && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
                        {msg.crop}
                      </span>
                    )}
                  </div>
                  {msg.error && (
                    <span className="inline-flex items-center gap-1 text-[10px] text-amber-700 font-semibold">
                      <AlertCircle className="w-3 h-3 text-amber-600" />
                      <span>{msg.error === 'NETWORK_ERROR' ? 'Network Notice' : 'Notice'}</span>
                    </span>
                  )}
                </div>
              )}

              {/* Message Body */}
              {msg.sender === 'user' ? (
                <div className="whitespace-pre-line text-xs font-normal">{msg.text}</div>
              ) : (
                <FormattedAssistantMessage content={msg.text} />
              )}

              {/* Retry Action on Error */}
              {msg.error && lastQuestion && (
                <div className="pt-2 border-t border-amber-200/60 flex items-center justify-between gap-2">
                  <span className="text-[11px] text-amber-800 font-medium">Question not completed</span>
                  <button
                    onClick={() => handleSend(lastQuestion)}
                    disabled={isLoading}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white transition-all cursor-pointer shadow-xs active:scale-95 disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                    <span>Retry Question</span>
                  </button>
                </div>
              )}

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="pt-2 border-t border-slate-200/60 text-[11px] text-slate-500 flex items-center gap-1.5">
                  <BookOpen className="w-3 h-3 text-teal-600 flex-shrink-0" />
                  <span>
                    <strong>Sources:</strong> {msg.sources.join(' • ')}
                  </span>
                </div>
              )}

              {/* Safety Disclaimer */}
              {msg.disclaimer && (
                <p className="text-[10px] text-slate-400 italic pt-1 border-t border-slate-200/40 leading-snug">
                  {msg.disclaimer}
                </p>
              )}

              {/* Timestamp */}
              <div
                className={`text-[10px] ${
                  msg.sender === 'user' ? 'text-emerald-200 text-right' : 'text-slate-400 text-left'
                }`}
              >
                {msg.timestamp}
              </div>
            </div>

            {msg.sender === 'user' && (
              <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center flex-shrink-0 shadow-xs">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-xl bg-emerald-600 text-white flex items-center justify-center flex-shrink-0 shadow-xs animate-pulse">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-center gap-2.5 shadow-2xs">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce" />
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.2s]" />
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.4s]" />
              <span className="ml-1 font-medium text-slate-700">
                Consulting Ask PlantCare with Gemini...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-2 shadow-xs flex items-center gap-2">
        <input
          type="text"
          value={inputValue}
          maxLength={1000}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSend();
          }}
          placeholder="Ask an agronomic question (e.g. spray schedule, disease prevention, irrigation)..."
          className="flex-1 px-4 py-2.5 text-xs text-slate-900 focus:outline-none bg-transparent"
        />
        <div className="text-[10px] text-slate-400 px-1 font-mono">
          {inputValue.length}/1000
        </div>
        <button
          onClick={() => handleSend()}
          disabled={!inputValue.trim() || isLoading}
          className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-emerald-600 text-white shadow-xs hover:bg-emerald-700 active:scale-95 transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
        >
          <span>Send</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
