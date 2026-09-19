'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import { fetchApi } from '@/lib/api';
import {
  Bot,
  User as UserIcon,
  Send,
  Sparkles,
  ShieldAlert,
  HelpCircle,
  Database,
  Trash2,
  Boxes,
  AlertTriangle,
  UserCheck,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';

interface AssistantSource {
  type: string;
  id?: number;
  code?: string;
  name?: string;
  details?: string;
}

interface AssistantChatResponse {
  answer: string;
  intent: string;
  sources: AssistantSource[];
  is_fallback: boolean;
}

interface ChatItem {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  intent?: string;
  sources?: AssistantSource[];
  isFallback?: boolean;
  timestamp: Date;
}

function AssistantContent() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatItem[]>([
    {
      id: 'welcome-1',
      sender: 'assistant',
      text: `Xin chào ${user?.full_name || ''}! Tôi là **Trợ lý AI DX-Asset**.\n\nTôi có thể giúp bạn tra cứu thông tin tài sản, kiểm tra người đang giữ thiết bị, tra cứu các sự cố kỹ thuật và xem lịch sử tài sản dựa trên dữ liệu thật từ cơ sở dữ liệu. Vui lòng chọn một câu hỏi gợi ý bên dưới hoặc nhập câu hỏi của bạn.`,
      intent: 'WELCOME',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const suggestedQuestions = [
    'Có bao nhiêu tài sản đang được cấp phát?',
    'Tài sản nào chưa được cấp phát?',
    'Có những sự cố nào đang xử lý?',
    'Lịch sử biến động tài sản gần đây?',
    'Thống kê tổng quan hệ thống tài sản?',
  ];

  const handleSend = async (messageToSend?: string) => {
    const text = (messageToSend || input).trim();
    if (!text || loading) return;

    const userMsg: ChatItem = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!messageToSend) setInput('');
    setLoading(true);

    try {
      const res = await fetchApi<AssistantChatResponse>('/assistant/chat', {
        method: 'POST',
        body: JSON.stringify({ message: text }),
      });

      const assistantMsg: ChatItem = {
        id: `ast-${Date.now()}`,
        sender: 'assistant',
        text: res.answer,
        intent: res.intent,
        sources: res.sources,
        isFallback: res.is_fallback,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatItem = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        text: `Đã xảy ra lỗi: ${err?.message || 'Không thể gửi câu hỏi đến dịch vụ Trợ lý AI.'}`,
        intent: 'ERROR',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: 'welcome-reset',
        sender: 'assistant',
        text: `Đã xóa lịch sử trò chuyện tạm thời. Bạn cần tra cứu thông tin tài sản nào tiếp theo?`,
        intent: 'WELCOME',
        timestamp: new Date(),
      },
    ]);
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-5xl w-full mx-auto p-4 sm:p-6 flex flex-col space-y-4">
        {/* Assistant Header Banner */}
        <div className="bg-gradient-to-r from-sky-900/40 via-indigo-900/30 to-slate-800/80 border border-slate-700/70 rounded-2xl p-5 shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="w-11 h-11 rounded-2xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 shrink-0">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold text-white">Trợ lý AI Quản lý Tài sản</h1>
                <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[11px] font-semibold">
                  Read-Only Mode
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5 flex items-center space-x-2">
                <Database className="w-3.5 h-3.5 text-sky-400 inline" />
                <span>Truy vấn thời gian thực trên PostgreSQL (Không tự bịa dữ liệu)</span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 self-end sm:self-auto">
            <button
              onClick={clearChat}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-semibold rounded-xl transition-all"
              title="Xóa trò chuyện"
            >
              <Trash2 className="w-3.5 h-3.5 text-slate-400" />
              <span>Xóa chat</span>
            </button>
          </div>
        </div>

        {/* Suggested Prompt Chips */}
        <div className="flex items-center space-x-2 overflow-x-auto pb-1 scrollbar-none">
          <span className="text-xs font-semibold text-slate-400 shrink-0 flex items-center space-x-1">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Gợi ý:</span>
          </span>
          {suggestedQuestions.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(q)}
              disabled={loading}
              className="px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 text-xs text-slate-200 hover:text-sky-300 whitespace-nowrap transition-all shrink-0 disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>

        {/* Chat Messages Window */}
        <div className="flex-1 bg-slate-800/80 border border-slate-700/70 rounded-2xl p-4 sm:p-6 shadow-xl flex flex-col space-y-4 min-h-[480px] max-h-[600px] overflow-y-auto">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start space-x-3 ${
                msg.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-xs font-bold border ${
                  msg.sender === 'user'
                    ? 'bg-sky-500/10 text-sky-400 border-sky-500/30'
                    : msg.intent === 'MUTATION_REJECTED'
                    ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                    : 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
                }`}
              >
                {msg.sender === 'user' ? <UserIcon className="w-4 h-4" /> : <Bot className="w-5 h-5" />}
              </div>

              {/* Bubble Body */}
              <div className="max-w-[85%] sm:max-w-[75%] space-y-2">
                <div
                  className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.sender === 'user'
                      ? 'bg-sky-600 text-white rounded-tr-none shadow-md'
                      : msg.intent === 'MUTATION_REJECTED'
                      ? 'bg-rose-950/40 border border-rose-500/40 text-rose-200 rounded-tl-none shadow-md'
                      : 'bg-slate-900/80 border border-slate-700/60 text-slate-200 rounded-tl-none shadow-md'
                  }`}
                >
                  {msg.intent === 'MUTATION_REJECTED' && (
                    <div className="flex items-center space-x-1.5 text-rose-400 font-bold mb-1.5 text-xs">
                      <ShieldAlert className="w-4 h-4 shrink-0" />
                      <span>Thông báo từ chối thao tác (Read-Only Guard)</span>
                    </div>
                  )}

                  {msg.text}

                  {/* Sources Cards */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-700/60 space-y-1.5">
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        Nguồn tham chiếu dữ liệu thật:
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {msg.sources.map((src, i) => (
                          <div
                            key={i}
                            className="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-[11px] text-sky-300 font-mono flex items-center space-x-1.5"
                          >
                            {src.type === 'asset' && <Boxes className="w-3 h-3 text-sky-400" />}
                            {src.type === 'incident' && <AlertTriangle className="w-3 h-3 text-rose-400" />}
                            <span>{src.code || src.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div
                  className={`text-[10px] text-slate-500 ${
                    msg.sender === 'user' ? 'text-right' : 'text-left'
                  }`}
                >
                  {msg.timestamp.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          ))}

          {/* Loading Indicator Bubble */}
          {loading && (
            <div className="flex items-start space-x-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0">
                <Bot className="w-5 h-5 animate-spin" />
              </div>
              <div className="p-4 bg-slate-900/80 border border-slate-700/60 rounded-2xl rounded-tl-none text-xs text-slate-400 flex items-center space-x-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-sky-400" />
                <span>Đang truy vấn cơ sở dữ liệu PostgreSQL...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-2.5 shadow-xl flex items-center space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            placeholder="Nhập câu hỏi tra cứu tài sản bằng tiếng Việt (ví dụ: Có bao nhiêu laptop đang cấp phát?)..."
            className="flex-1 bg-slate-900/80 border border-slate-700/60 rounded-xl px-4 py-3 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-all disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className="px-4 py-3 bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 text-white font-semibold rounded-xl text-xs sm:text-sm flex items-center space-x-2 transition-all shadow-lg shadow-sky-500/20 disabled:shadow-none shrink-0"
          >
            <span>Gửi</span>
            <Send className="w-4 h-4" />
          </button>
        </div>
      </main>
    </div>
  );
}

export default function AssistantPage() {
  return (
    <ProtectedRoute>
      <AssistantContent />
    </ProtectedRoute>
  );
}
