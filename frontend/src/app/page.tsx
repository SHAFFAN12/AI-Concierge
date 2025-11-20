"use client";
import { useState, useEffect, useRef } from "react";
import { Send, Bot, User, Mic, MicOff } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    // Load chat history from localStorage on startup
    const savedMessages = localStorage.getItem("chat_history");
    if (savedMessages) {
      setMessages(JSON.parse(savedMessages));
    } else {
      setMessages([
        { role: "bot", text: "👋 Hi there! I’m your AI Concierge. How can I assist you today?" },
      ]);
    }
  }, []);

  useEffect(() => {
    // Save chat history to localStorage whenever it changes
    localStorage.setItem("chat_history", JSON.stringify(messages));
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Speech Recognition and Text-to-Speech setup (remains the same)
  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)
    ) {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onresult = (event: any) => {
        setInput(event.results[0][0].transcript);
      };

      recognition.onend = () => setListening(false);
      recognition.onerror = (event: any) => {
        console.error("Speech recognition error:", event.error);
        setListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  function speak(text: string) {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-US";
      window.speechSynthesis.speak(utterance);
    }
  }

  async function sendMessage() {
    if (!input.trim()) return;
    const userMsg = { role: "user", text: input };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: input,
          history: newMessages,
          current_url: window.location.href,
        }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      
      const replyText = data.note || "Sorry, I didn’t quite catch that.";
      const botMsg = { role: "bot", text: replyText };
      setMessages((prev) => [...prev, botMsg]);
      speak(replyText);

      // Handle actions from the backend
      if (data.action) {
        handleBackendAction(data.action);
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

  function handleBackendAction(action: { type: string; [key: string]: any }) {
    console.log("Received action from backend:", action);
    switch (action.type) {
      case "click":
        // In a real scenario, you would use the selector to click the element
        alert(`AI wants to click on element: ${action.selector}`);
        break;
      case "fill_form":
        // In a real scenario, you would use the selectors to fill the form
        alert(`AI wants to fill a form with these details: ${JSON.stringify(action.fields)}`);
        break;
      // Add more cases for other actions here
      default:
        console.warn("Unknown action type:", action.type);
    }
  }

  const startListening = () => {
    if (recognitionRef.current) {
      setListening(true);
      recognitionRef.current.start();
    } else {
      alert("Speech recognition not supported in this browser.");
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) recognitionRef.current.stop();
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-white to-blue-50 text-gray-900">
      {/* HEADER */}
      <header className="p-6 bg-white shadow-md flex justify-between items-center sticky top-0 z-10">
        <h1 className="text-2xl font-extrabold text-blue-600">AI Concierge</h1>
        <nav className="flex items-center space-x-6">
          <a href="#features" className="hover:text-blue-600 transition-colors">Features</a>
          <a href="#demo" className="hover:text-blue-600 transition-colors">Demo</a>
          <a
            href="#contact"
            className="bg-blue-600 text-white px-5 py-2 rounded-full hover:bg-blue-700 transition-all shadow"
          >
            Contact
          </a>
        </nav>
      </header>

      {/* HERO SECTION */}
      <main className="flex-1 flex flex-col items-center justify-center text-center p-8">
        <section className="max-w-3xl">
          <h2 className="text-5xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-500">
            Your Personal AI Assistant
          </h2>
          <p className="mt-4 text-lg text-gray-600 leading-relaxed">
            Navigate websites, book appointments, and get instant help — powered by AI.
          </p>
          <a
            href="#demo"
            className="mt-8 inline-flex items-center justify-center bg-blue-600 text-white px-8 py-3 rounded-full text-lg font-semibold hover:bg-blue-700 shadow-md transition-all"
          >
            Try the Demo
          </a>
        </section>
      </main>

      {/* CHAT SECTION */}
      <section id="demo" className="py-20 px-4 bg-white">
        <div className="max-w-4xl mx-auto">
          <h3 className="text-4xl font-bold text-center mb-10 text-gray-800">AI Concierge in Action</h3>

          <div className="bg-white border border-gray-200 rounded-2xl shadow-xl overflow-hidden">
            <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-purple-50 flex justify-between items-center">
              <h4 className="text-lg font-semibold text-gray-700">Chat with your assistant</h4>
            </div>

            <div className="p-4 h-96 overflow-y-auto space-y-4">
              {messages.map((m, i) => (
                <div key={i} className={`flex items-start gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                  {m.role === "bot" && <Bot className="w-6 h-6 text-blue-600" />}
                  <div
                    className={`rounded-xl px-4 py-2 max-w-[80%] shadow-sm ${
                      m.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-800"
                    }`}
                  >
                    <p className="text-sm">{m.text}</p>
                  </div>
                  {m.role === "user" && <User className="w-6 h-6 text-gray-500" />}
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-gray-200 flex items-center gap-2 bg-gray-50">
              <input
                className="flex-1 bg-white rounded-full px-4 py-2 border border-gray-300 focus:ring-2 focus:ring-blue-400 focus:outline-none transition-all"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                placeholder="Ask something..."
                disabled={loading}
              />
              <button
                onClick={sendMessage}
                disabled={loading}
                className="bg-blue-600 text-white px-4 py-2 rounded-full hover:bg-blue-700 transition-all flex items-center shadow"
              >
                {loading ? (
                  <span className="text-sm">Thinking...</span>
                ) : (
                  <>
                    <Send className="w-5 h-5 mr-2" /> Send
                  </>
                )}
              </button>

              <button
                onClick={listening ? stopListening : startListening}
                className="bg-gray-200 text-gray-800 px-3 py-2 rounded-full hover:bg-gray-300 transition-all"
              >
                {listening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="py-20 px-4 bg-gradient-to-b from-blue-50 to-white">
        <div className="max-w-5xl mx-auto text-center">
          <h3 className="text-4xl font-bold mb-10 text-gray-800">Why Choose AI Concierge?</h3>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 bg-white rounded-xl shadow hover:shadow-lg transition">
              <h4 className="text-xl font-semibold text-blue-600 mb-2">Smart Booking</h4>
              <p className="text-gray-600">Automatically fills and submits booking forms across websites.</p>
            </div>
            <div className="p-6 bg-white rounded-xl shadow hover:shadow-lg transition">
              <h4 className="text-xl font-semibold text-blue-600 mb-2">Voice Commands</h4>
              <p className="text-gray-600">Talk naturally — your assistant listens and responds in real time.</p>
            </div>
            <div className="p-6 bg-white rounded-xl shadow hover:shadow-lg transition">
              <h4 className="text-xl font-semibold text-blue-600 mb-2">Seamless Integration</h4>
              <p className="text-gray-600">Embed on any website effortlessly and personalize the experience.</p>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer id="contact" className="p-6 bg-white border-t text-center text-gray-500">
        <p>&copy; 2025 AI Concierge. All rights reserved.</p>
      </footer>
    </div>
  );
}