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

export default function Home() {
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [userId, setUserId] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // ✅ Setup SpeechRecognition if available
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
        setInput(transcript); // voice input → textbox me aa jaye
      };

      recognition.onend = () => {
        console.log("Speech recognition ended.");
        setListening(false);
      };

      recognition.onerror = (event: any) => {
        console.error("Speech recognition error:", event.error);
        setListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  // ✅ Speak function (TTS)
  function speak(text: string) {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-US";
      window.speechSynthesis.speak(utterance);
    }
  }

  useEffect(() => {
    setUserId(getUserId());
    setMessages([
      {
        role: "bot",
        text: "Hello! I'm your AI Concierge. How can I help you today?",
      },
    ]);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    if (!input.trim()) return;
    const userMsg = { role: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
          message: input,
        }),
      });

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }

      const data = await res.json();

      // ✅ backend ke sahi fields check karo
      const replyText =
        data?.result?.note || // booking/search ka output
        data?.plan?.message || // simple reply
        "Sorry, I didn't understand that.";

      const botMsg = { role: "bot", text: replyText };
      setMessages((prev) => [...prev, botMsg]);

      // ✅ Voice output
      speak(replyText);
    } catch (err: any) {
      const botMsg = { role: "bot", text: `❌ Error: ${err.message}` };
      setMessages((prev) => [...prev, botMsg]);
    } finally {
      setLoading(false);
    }
  }

  const startListening = () => {
    if (recognitionRef.current) {
      console.log("Starting speech recognition...");
      setListening(true);
      recognitionRef.current.start();
    } else {
      alert("Speech recognition not supported in this browser.");
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setListening(false);
  };

  return (
    <div className="dark min-h-screen flex flex-col">
      <header className="p-4 border-b border-border flex justify-between items-center">
        <h1 className="text-2xl font-bold text-primary">AI Concierge</h1>
        <div className="flex items-center space-x-4">
          <a href="#features" className="text-secondary-foreground hover:text-primary">
            Features
          </a>
          <a href="#demo" className="text-secondary-foreground hover:text-primary">
            Demo
          </a>
          <a
            href="#contact"
            className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90"
          >
            Contact
          </a>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center p-4 text-center">
        <section className="max-w-3xl">
          <h2 className="text-5xl font-bold tracking-tighter">Your Personal AI Assistant</h2>
          <p className="mt-4 text-lg text-secondary-foreground">
            Navigate websites, book appointments, and get information instantly. Your AI Concierge is here to help.
          </p>
          <a
            href="#demo"
            className="mt-8 inline-flex items-center justify-center bg-primary text-primary-foreground px-6 py-3 rounded-md text-lg font-medium hover:bg-primary/90"
          >
            Try the Demo
          </a>
        </section>
      </main>

      <section id="demo" className="py-20 px-4 bg-secondary">
        <div className="max-w-4xl mx-auto">
          <h3 className="text-4xl font-bold text-center mb-12">AI Concierge in Action</h3>
          <div className="bg-card rounded-lg shadow-lg overflow-hidden">
            <div className="p-4 border-b border-border">
              <h4 className="text-lg font-semibold">Chat with your assistant</h4>
            </div>
            <div className="p-4 h-96 overflow-y-auto space-y-4">
              {messages.map((m, i) => (
                <div key={i} className={`flex items-start gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                  {m.role === "bot" && <Bot className="w-6 h-6 text-primary" />}
                  <div
                    className={`rounded-lg px-4 py-2 max-w-[80%] ${
                      m.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-input"
                    }`}
                  >
                    <p className="text-sm">{m.text}</p>
                  </div>
                  {m.role === "user" && <User className="w-6 h-6 text-secondary-foreground" />}
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Input + Buttons */}
            <div className="p-4 border-t border-border flex items-center gap-2">
              <input
                className="flex-1 bg-input rounded-l-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                placeholder="Ask me anything..."
                disabled={loading}
              />
              <button
                onClick={sendMessage}
                disabled={loading}
                className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 flex items-center"
              >
                {loading ? (
                  <span className="text-sm">Thinking...</span>
                ) : (
                  <>
                    <Send className="w-5 h-5 mr-2" />
                    Send
                  </>
                )}
              </button>

              {/* 🎤 Mic Button */}
              <button
                onClick={listening ? stopListening : startListening}
                className="bg-gray-700 text-white px-3 py-2 rounded-md hover:bg-gray-600"
              >
                {listening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="py-20 px-4">
        {/* features same as before */}
      </section>

      <footer id="contact" className="p-4 border-t border-border text-center text-secondary-foreground">
        <p>&copy; 2025 AI Concierge. All rights reserved.</p>
      </footer>
    </div>
  );
}
