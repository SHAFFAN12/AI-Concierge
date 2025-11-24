"use client";

import React, { useState, useEffect, useRef } from "react";
import { FiSend, FiTrash2, FiMic, FiMicOff, FiCpu, FiUser } from "react-icons/fi";
import ReactMarkdown from "react-markdown";
import { saveMessage, getHistory, clearHistory, ChatMessage } from "../utils/storage";
import { scanSiteNavigation } from "../utils/siteScanner";

// --- Components ---

const MessageBubble = ({ role, content }: { role: "user" | "assistant"; content: string }) => {
  const isUser = role === "user";
  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"} mb-6 animate-fade-in-up`}>
      <div className={`flex max-w-[85%] ${isUser ? "flex-row-reverse" : "flex-row"} gap-3`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${isUser
          ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
          : "bg-purple-500/20 text-purple-400 border border-purple-500/30"
          }`}>
          {isUser ? <FiUser size={16} /> : <FiCpu size={16} />}
        </div>

        {/* Bubble */}
        <div
          className={`p-4 rounded-2xl shadow-lg ${isUser
            ? "glass-bubble-user text-white rounded-tr-none"
            : "glass-bubble-assistant text-gray-100 rounded-tl-none"
            }`}
        >
          <div className="prose prose-invert prose-sm max-w-none leading-relaxed">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
};

const TypingIndicator = () => (
  <div className="flex justify-start mb-6 animate-fade-in">
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-purple-500/20 text-purple-400 border border-purple-500/30 flex items-center justify-center">
        <FiCpu size={16} />
      </div>
      <div className="glass-bubble-assistant p-4 rounded-2xl rounded-tl-none flex items-center space-x-2">
        <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
        <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
        <div className="w-1.5 h-1.5 bg-pink-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  </div>
);

// --- Main Component ---

export default function ChatWidget() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // Load history on mount
  useEffect(() => {
    const loadHistory = async () => {
      const history = await getHistory();
      if (history.length > 0) {
        setMessages(history);
      } else {
        // Initial greeting if no history
        const initialMsg: ChatMessage = {
          role: "assistant",
          content: "System Online. I am your AI Concierge. How may I assist you today?",
          timestamp: Date.now()
        };
        setMessages([initialMsg]);
        saveMessage(initialMsg);
      }
    };
    loadHistory();
  }, []);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Voice Recognition Setup
  useEffect(() => {
    if (typeof window !== "undefined" && (window as any).webkitSpeechRecognition) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = "en-US";

      recognitionRef.current.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setIsListening(false);
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error("Speech recognition error", event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
    } else {
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  const speakText = (text: string) => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(v => v.name.includes("Google US English") || v.name.includes("Samantha"));
      if (preferredVoice) utterance.voice = preferredVoice;
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleClearChat = async () => {
    await clearHistory();
    setMessages([{
      role: "assistant",
      content: "Memory purged. Ready for new instructions.",
      timestamp: Date.now()
    }]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: ChatMessage = { role: "user", content: input, timestamp: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    saveMessage(userMsg);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: input,
          history: messages,
          current_url: window.location.href,
          site_navigation: scanSiteNavigation()
        }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessageContent = "";

      const assistantMsgTimestamp = Date.now();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", timestamp: assistantMsgTimestamp },
      ]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const dataString = line.slice(6);
              if (dataString.trim() === "[DONE]") continue;

              const data = JSON.parse(dataString);

              if (data.error) {
                console.error("Backend Error:", data.error);
                assistantMessageContent = `⚠️ Error: ${data.error}`;
              } else if (data.content) {
                const cleanContent = data.content.replace(/<tool_code>[\s\S]*?<\/tool_code>/g, "")
                  .replace(/<tool_output>[\s\S]*?<\/tool_output>/g, "");
                if (cleanContent) {
                  assistantMessageContent += cleanContent;
                }
              }

              setMessages((prev) => {
                const newHistory = [...prev];
                const lastMsg = newHistory[newHistory.length - 1];
                if (lastMsg.role === "assistant") {
                  lastMsg.content = assistantMessageContent;
                }
                return newHistory;
              });

            } catch (err) {
              console.error("Error parsing SSE:", err);
            }
          }
        }
      }

      saveMessage({ role: "assistant", content: assistantMessageContent, timestamp: assistantMsgTimestamp });
      speakText(assistantMessageContent);

    } catch (error) {
      console.error("Error sending message:", error);
      const errorMsg: ChatMessage = { role: "assistant", content: "Connection interrupted.", timestamp: Date.now() };
      setMessages((prev) => [...prev, errorMsg]);
      saveMessage(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-5xl mx-auto p-4 md:p-6 relative overflow-hidden">
      {/* Background Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-purple-600/20 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-cyan-600/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Header */}
      <div className="glass-panel rounded-2xl p-4 mb-6 flex items-center justify-between relative z-10 neon-border">
        <div className="flex items-center space-x-4">
          <div className="relative">
            <div className="absolute inset-0 bg-cyan-500 blur-md opacity-50 animate-pulse"></div>
            <div className="relative w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg">
              <FiCpu className="text-white text-xl" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide font-mono">AI_CONCIERGE<span className="animate-pulse text-cyan-400">_</span></h1>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_5px_#22c55e]"></span>
              <p className="text-xs text-cyan-200/70 font-mono tracking-wider">SYSTEM ONLINE</p>
            </div>
          </div>
        </div>
        <button
          onClick={handleClearChat}
          className="p-2.5 text-cyan-400/70 hover:text-red-400 hover:bg-red-500/10 transition-all rounded-lg border border-transparent hover:border-red-500/30"
          title="Purge Memory"
        >
          <FiTrash2 size={18} />
        </button>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto mb-6 pr-2 scrollbar-thin relative z-10">
        {messages.map((msg, idx) => (
          <MessageBubble key={idx} role={msg.role} content={msg.content} />
        ))}
        {isLoading && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="relative z-10">
        <div className="glass-panel rounded-2xl p-2 flex items-center gap-2 shadow-2xl border border-white/10 focus-within:border-cyan-500/50 transition-colors duration-300">
          <button
            type="button"
            onClick={toggleListening}
            className={`p-3 rounded-xl transition-all duration-300 ${isListening
              ? "bg-red-500/20 text-red-400 animate-pulse border border-red-500/50"
              : "hover:bg-cyan-500/10 text-gray-400 hover:text-cyan-400"
              }`}
            title="Voice Input"
          >
            {isListening ? <FiMicOff size={20} /> : <FiMic size={20} />}
          </button>

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isListening ? "Listening..." : "Enter command..."}
            className="flex-1 bg-transparent border-none focus:ring-0 text-white placeholder-gray-600 px-2 py-3 font-mono text-sm"
            disabled={isLoading}
          />

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="p-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-105 active:scale-95"
          >
            <FiSend size={18} />
          </button>
        </div>
      </form>
    </div>
  );
}
