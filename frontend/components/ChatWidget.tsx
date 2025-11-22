"use client";

import { useState, useEffect, useRef } from "react";
import {
  FiSend,
  FiX,
  FiMessageSquare,
  FiChevronDown,
  FiChevronUp,
} from "react-icons/fi";
import { BsRobot, BsPersonCircle } from "react-icons/bs";
import { AiOutlineRobot } from "react-icons/ai";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatWidget() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isAssistantTyping, setIsAssistantTyping] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [currentUrl, setCurrentUrl] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const { type, payload } = event.data;
      if (type === "page_info") setCurrentUrl(payload.url);
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsAssistantTyping(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: input,
          history: messages,
          current_url: currentUrl,
        }),
      });

      if (!response.body) throw new Error("Response body is null");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let assistantMessage: Message = { role: "assistant", content: "" };
      setMessages((prev) => [...prev, assistantMessage]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          setIsAssistantTyping(false);
          break;
        }

        const chunk = decoder.decode(value);
        const events = chunk.split("\n\n").filter(Boolean);

        for (const event of events) {
          if (event.startsWith("data: ")) {
            const dataString = event.substring(6);
            if (dataString === "[DONE]") {
              setIsAssistantTyping(false);
              reader.cancel();
              break;
            }

            const data = JSON.parse(dataString);
            console.log("Received data:", data);
            
            if (data.ops) {
              data.ops.forEach((op: any) => {
                // Handle streaming output from agent
                if (op.path === "/logs/Agent/streamed_output/-" && op.value) {
                  // Filter out XML tool tags
                  const cleanValue = op.value;
                  // Only add if it's not a tool invocation tag
                  if (!cleanValue.includes("<scrape_webpage") && 
                      !cleanValue.includes("</scrape_webpage>") &&
                      !cleanValue.includes("<search_web") &&
                      !cleanValue.includes("</search_web>") &&
                      !cleanValue.includes("<fill_form") &&
                      !cleanValue.includes("</fill_form>") &&
                      !cleanValue.includes("<click_element") &&
                      !cleanValue.includes("</click_element>")) {
                    assistantMessage.content += cleanValue;
                    setMessages((prev) => {
                      const updated = [...prev];
                      updated[updated.length - 1] = { ...assistantMessage };
                      return updated;
                    });
                  }
                }
                // Handle final output - only use if there's no streamed content
                if (op.path === "/logs/Agent/final_output" && op.value?.output) {
                  // Clean the final output from XML tags
                  let cleanOutput = op.value.output;
                  // Remove any XML tool invocation tags
                  cleanOutput = cleanOutput.replace(/<scrape_webpage[^>]*>[\s\S]*?<\/scrape_webpage>/g, '');
                  cleanOutput = cleanOutput.replace(/<search_web[^>]*>[\s\S]*?<\/search_web>/g, '');
                  cleanOutput = cleanOutput.replace(/<fill_form[^>]*>[\s\S]*?<\/fill_form>/g, '');
                  cleanOutput = cleanOutput.replace(/<click_element[^>]*>[\s\S]*?<\/click_element>/g, '');
                  cleanOutput = cleanOutput.replace(/<[^>]+>/g, ''); // Remove any remaining XML tags
                  cleanOutput = cleanOutput.trim();
                  
                  // Only use if we don't have content or the current content is just tool calls
                  if (!assistantMessage.content || assistantMessage.content.trim() === "" || 
                      assistantMessage.content.includes("<scrape_webpage") || 
                      assistantMessage.content.includes("<search_web")) {
                    assistantMessage.content = cleanOutput;
                  } else if (cleanOutput && cleanOutput !== assistantMessage.content) {
                    // If final output is different and meaningful, append or replace
                    assistantMessage.content = cleanOutput;
                  }
                  
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = { ...assistantMessage };
                    return updated;
                  });
                  
                  // Stop typing indicator when final output is received
                  setIsAssistantTyping(false);
                }
                // Handle legacy message format
                if (op.path === "/messages/-" && op.value?.content) {
                  assistantMessage.content += op.value.content;
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = { ...assistantMessage };
                    return updated;
                  });
                }
                // Handle actions (form fill, clicks, etc.)
                if (op.path === "/actions/-") {
                  window.parent.postMessage(op.value, "*");
                }
              });
            }
          }
        }
      }
    } catch (e) {
      setMessages((prev) => [...prev, { role: "assistant", content: "Error: Could not connect." }]);
      setIsAssistantTyping(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-gradient-to-br from-black via-gray-900 to-black text-white rounded-3xl shadow-2xl border border-yellow-500/30 overflow-hidden backdrop-blur-xl">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-gradient-to-r from-yellow-500/10 to-yellow-600/10 border-b border-yellow-500/30 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-yellow-500 to-yellow-400 rounded-full blur-md opacity-80 animate-pulse"></div>
            <div className="relative bg-gradient-to-br from-yellow-500 to-yellow-600 p-2.5 rounded-full shadow-lg shadow-yellow-500/50">
              <AiOutlineRobot className="text-black text-lg" />
            </div>
          </div>
          <div>
            <h2 className="text-lg font-bold bg-gradient-to-r from-yellow-400 to-yellow-200 bg-clip-text text-transparent">
              AI Concierge
            </h2>
            <p className="text-xs text-yellow-300/70">Here whenever you need</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-2 rounded-xl hover:bg-yellow-500/20 transition text-yellow-400"
          >
            {isMinimized ? <FiChevronUp /> : <FiChevronDown />}
          </button>
          <button className="p-2 rounded-xl hover:bg-red-500/20 transition text-yellow-400 hover:text-red-400">
            <FiX />
          </button>
        </div>
      </div>

      {/* Chat Window */}
      {!isMinimized && (
        <>
          <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center text-center opacity-60 h-full">
                <div className="relative">
                  <div className="absolute inset-0 bg-yellow-500 rounded-full blur-2xl opacity-30"></div>
                  <FiMessageSquare className="relative text-5xl text-yellow-400 mb-3" />
                </div>
                <p className="font-semibold text-yellow-200">Start a conversation</p>
                <p className="text-sm text-yellow-300/70">Ask anything you want!</p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-2 animate-fade-in ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                <div className={`p-2 rounded-full shadow-lg ${msg.role === "user" ? "bg-gradient-to-br from-yellow-500 to-yellow-600 shadow-yellow-500/50" : "bg-gradient-to-br from-gray-700 to-gray-800 border border-yellow-500/30 shadow-yellow-500/20"}`}>
                  {msg.role === "user" ? (
                    <BsPersonCircle className="text-black text-lg" />
                  ) : (
                    <BsRobot className="text-yellow-400 text-lg" />
                  )}
                </div>

                <div className="max-w-[75%]">
                  <div
                    className={`px-4 py-3 rounded-2xl shadow-lg text-sm whitespace-pre-wrap break-words backdrop-blur-xl ${
                      msg.role === "user"
                        ? "bg-gradient-to-br from-yellow-500 to-yellow-600 text-black rounded-tr-md shadow-yellow-500/30"
                        : "bg-gradient-to-br from-gray-800 to-gray-900 border border-yellow-500/20 rounded-tl-md text-yellow-50"
                    }`}
                  >
                    {msg.content}
                  </div>
                  <p className="text-[10px] text-yellow-400/50 mt-1">
                    {new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
              </div>
            ))}

            {isAssistantTyping && (
              <div className="flex gap-2 animate-fade-in">
                <div className="p-2 rounded-full bg-gradient-to-br from-gray-700 to-gray-800 border border-yellow-500/30 shadow-lg shadow-yellow-500/20">
                  <BsRobot className="text-yellow-400 text-lg" />
                </div>
                <div className="px-4 py-3 rounded-2xl bg-gradient-to-br from-gray-800 to-gray-900 border border-yellow-500/20 shadow-lg">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce"></span>
                    <span className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce [animation-delay:150ms]"></span>
                    <span className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce [animation-delay:300ms]"></span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSubmit} className="p-4 bg-gradient-to-r from-yellow-500/5 to-yellow-600/5 border-t border-yellow-500/30 backdrop-blur-xl">
            <div className="flex items-center gap-3 bg-gray-900/50 rounded-2xl px-3 py-2 border border-yellow-500/30 focus-within:border-yellow-500/70 transition-all duration-200">
              <input
                className="flex-1 bg-transparent outline-none text-sm text-yellow-50 placeholder-yellow-400/40"
                placeholder="Type a message..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isAssistantTyping}
              />
              <button
                type="submit"
                disabled={!input.trim() || isAssistantTyping}
                className="p-3 rounded-xl bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-400 hover:to-yellow-500 shadow-lg shadow-yellow-500/50 transition-all duration-200 disabled:opacity-40 disabled:shadow-none disabled:cursor-not-allowed group"
              >
                <FiSend className="text-black group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  );
}
