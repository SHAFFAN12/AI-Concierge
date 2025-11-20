"use client";
import ChatInterface from "../../../components/ChatInterface";
import "../globals.css"; // Import global styles for tailwind and base styles

export default function EmbedWidgetPage() {
  return (
    <html lang="en">
      <head>
        <title>AI Concierge Widget</title>
      </head>
      <body>
        <div className="h-screen w-screen flex flex-col">
          <ChatInterface />
        </div>
      </body>
    </html>
  );
}
