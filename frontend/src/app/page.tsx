"use client";
import ChatInterface from "../../components/ChatInterface";

export default function Home() {
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
        <div className="max-w-4xl mx-auto h-[600px] flex"> {/* Added h-[600px] and flex */}
          <ChatInterface />
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