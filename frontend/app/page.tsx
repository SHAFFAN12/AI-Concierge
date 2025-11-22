import ChatWidget from "@/components/ChatWidget";

export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <main className="w-full max-w-md h-[600px] border rounded-lg">
        <ChatWidget />
      </main>
    </div>
  );
}