"use client";
import { useState, useEffect, useRef } from "react";
import { Send, Bot, User, Mic, MicOff } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getUserId() {
  if (typeof window !== "undefined") {
    let userId = localStorage.getItem("user_id");
    if (!userId) {
      userId = Math.random().toString(36).substring(2);
      localStorage.setItem("user_id", userId);
    }
    return userId;
  }
  return "anonymous";
}

export default function WidgetPage() {
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [userId, setUserId] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [pageInfo, setPageInfo] = useState<{ url: string; domain: string } | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // 🎤 Speech recognition
  useEffect(() => {
    if (typeof window !== "undefined" && "webkitSpeechRecognition" in window) {
      const SpeechRecognition =
        window.SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        console.log("Speech recognized:", transcript);
        setInput(transcript);
      };

      recognition.onend = () => setListening(false);
      recognition.onerror = (event: any) => {
        console.error("Speech recognition error:", event.error);
        setListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  // 🗣️ Text to speech
  function speak(text: string) {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-US";
      window.speechSynthesis.speak(utterance);
    }
  }

  // 👋 Initial bot message
  useEffect(() => {
    setUserId(getUserId());
    setMessages([
      { role: "bot", text: "👋 Hi there! I’m your AI Concierge. How can I help you today?" },
    ]);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 🌐 Receive page info
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === "page_info") {
        const { url, domain } = event.data.payload;
        console.log("📩 Received page info:", url, domain);
        setPageInfo({ url, domain });
        localStorage.setItem("current_page_url", url);
        localStorage.setItem("current_page_domain", domain);
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  // 🚀 Send message
  async function sendMessage() {
    if (!input.trim()) return;
    const userMsg = { role: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          message: input,
          current_url: pageInfo?.url || localStorage.getItem("current_page_url"),
          domain: pageInfo?.domain || localStorage.getItem("current_page_domain"),
        }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();

      const replyText =
        data?.result?.note ||
        data?.plan?.message ||
        data?.message ||
        "Sorry, I didn’t understand that.";

      const botMsg = { role: "bot", text: replyText };
      setMessages((prev) => [...prev, botMsg]);
      speak(replyText);

      if (data.action && data.action.type === "autofill") {
        console.log("📤 Sending autofill action to parent page:", data.action);
        window.parent.postMessage(data.action, "*");
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: `❌ Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const startListening = () => {
    if (recognitionRef.current) {
      setListening(true);
      recognitionRef.current.start();
    } else alert("Speech recognition not supported.");
  };

  const stopListening = () => {
    if (recognitionRef.current) recognitionRef.current.stop();
    setListening(false);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 via-white to-blue-100 text-gray-800">
      <div className="w-full max-w-2xl bg-white shadow-xl rounded-2xl flex flex-col overflow-hidden border border-gray-200">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-500 text-white py-3 px-5 flex items-center justify-between">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Bot className="w-5 h-5" /> AI Concierge
          </h2>
          <span className="text-sm opacity-80">powered by LLM</span>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 p-5 overflow-y-auto space-y-4 bg-gray-50">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`px-4 py-2 rounded-xl shadow-sm max-w-[75%] ${
                  m.role === "user"
                    ? "bg-blue-600 text-white rounded-br-none"
                    : "bg-white border border-gray-200 text-gray-800 rounded-bl-none"
                }`}
              >
                <p className="text-sm leading-relaxed">{m.text}</p>
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Input Bar */}
        <div className="border-t bg-white p-3 flex items-center gap-2">
          <input
            type="text"
            placeholder="Type your message..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-full transition"
          >
            {loading ? "..." : <Send className="w-5 h-5" />}
          </button>
          <button
            onClick={listening ? stopListening : startListening}
            className={`p-2 rounded-full ${
              listening ? "bg-red-500 hover:bg-red-600" : "bg-gray-200 hover:bg-gray-300"
            } transition`}
          >
            {listening ? <MicOff className="w-5 h-5 text-white" /> : <Mic className="w-5 h-5 text-gray-700" />}
          </button>
        </div>
      </div>
    </div>
  );
}
