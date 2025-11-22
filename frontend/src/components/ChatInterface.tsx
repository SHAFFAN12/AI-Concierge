"use client";
import { useState, useEffect, useRef, Fragment } from "react";
import { Send, Bot, User, Mic, MicOff } from "lucide-react";
import { Dialog, Transition } from '@headlessui/react'; // For modal/dialog

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Helper function to find element, flash it, and return
const findElementAndFlash = (selector: string) => {
    const element = document.querySelector(selector) as HTMLElement;
    if (element) {
        element.style.outline = '3px solid #3b82f6'; // Blue flash
        element.style.transition = 'outline 1s ease-out';
        setTimeout(() => {
            element.style.outline = '';
        }, 1000);
    }
    return element;
};

const handleClick = (selector: string) => {
    try {
        const element = findElementAndFlash(selector);
        if (element) {
            element.click();
            return { success: true, message: `Clicked element with selector: ${selector}` };
        } else {
            return { success: false, message: `Element not found for click: ${selector}` };
        }
    } catch (error) {
        return { success: false, message: `Error clicking element ${selector}: ${error}` };
    }
};

const handleFillForm = (fields: Array<{ selector: string; value: string }>) => {
    const results = [];
    for (const field of fields) {
        try {
            const element = findElementAndFlash(field.selector) as
                | HTMLInputElement
                | HTMLTextAreaElement
                | HTMLSelectElement;
            if (element) {
                element.value = field.value;
                // Dispatch a change event for React to pick up the change
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                results.push({ selector: field.selector, success: true });
            } else {
                results.push({ selector: field.selector, success: false, message: "Element not found" });
            }
        } catch (error) {
            results.push({ selector: field.selector, success: false, message: `Error filling field: ${error}` });
        }
    }
    return { success: results.every(r => r.success), details: results };
};


export default function ChatInterface() {
    const [messages, setMessages] = useState<{ role: string; text: string; id?: string; streaming?: boolean; temp?: boolean }[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [listening, setListening] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);
    const recognitionRef = useRef<any>(null);

    // State for Action Confirmation Modal
    const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
    const [actionToConfirm, setActionToConfirm] = useState<any>(null);

    useEffect(() => {
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
        localStorage.setItem("chat_history", JSON.stringify(messages.filter(msg => !msg.temp))); // Don't save temp messages
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

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
        const tempBotMsgId = `bot-stream-${Date.now()}`;
        
        setMessages((prev) => [...prev, userMsg, { role: "bot", text: "", id: tempBotMsgId, streaming: true }]);
        setInput("");
        setLoading(true);

        try {
            const res = await fetch(`${API_URL}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: input,
                    history: messages.filter(msg => !msg.streaming && !msg.temp), // Send non-streaming, non-temp history
                    current_url: window.location.href,
                }),
            });

            if (!res.ok) throw new Error(`API error: ${res.status}`);
            if (!res.body) throw new Error('Response body is null');

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let fullBotResponse = "";
            let currentMessageText = "";
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;
                
                const lines = buffer.split('\n');
                buffer = lines.pop() || ""; // Keep incomplete line in buffer
                
                for (const line of lines) {
                    const trimmedLine = line.trim();
                    if (!trimmedLine || trimmedLine === '') continue;
                    
                    if (trimmedLine.startsWith('data:')) {
                        const eventString = trimmedLine.substring(5).trim(); // Remove 'data:' prefix and trim
                        if (!eventString) continue;
                        
                        try {
                            console.log('About to parse:', eventString);
                            const data = JSON.parse(eventString);
                            console.log('Parsed successfully:', data);

                        if (data.ops) { 
                            for (const op of data.ops) {
                                if (op.path === '/logs/Agent/final_output') {
                                    fullBotResponse = op.value.output;
                                    setMessages((prevMessages) =>
                                        prevMessages.map((msg) =>
                                            msg.id === tempBotMsgId ? { ...msg, text: fullBotResponse, streaming: false } : msg
                                        )
                                    );
                                    speak(fullBotResponse);
                                    if (op.value.action) {
                                        setActionToConfirm(op.value.action);
                                        setIsConfirmModalOpen(true);
                                    }
                                } else if (op.path === '/logs/Agent/streamed_output/-') {
                                    currentMessageText += op.value;
                                    setMessages((prevMessages) =>
                                        prevMessages.map((msg) =>
                                            msg.id === tempBotMsgId ? { ...msg, text: currentMessageText } : msg
                                        )
                                    );
                                } else if (op.path.includes('/logs/Agent/steps/')) {
                                    let stepMessage = "";
                                    if (op.path.includes('/start')) {
                                        if (op.value.name === 'Tool:DuckDuckGoSearchRun') {
                                            stepMessage = "AI is searching the web...";
                                        } else if (op.value.name === 'Tool:scrape_webpage') {
                                            stepMessage = "AI is analyzing the page...";
                                        } else if (op.value.name === 'LLM:ChatGroq') {
                                            stepMessage = "AI is thinking...";
                                        } else {
                                            stepMessage = `AI is performing step: ${op.value.name}...`;
                                        }
                                        setMessages((prevMessages) => [...prevMessages, { role: "bot", text: stepMessage, streaming: true, temp: true, id: `step-${Date.now()}` }]);
                                    } else if (op.path.includes('/end') || op.path.includes('/streamed_output/-')) {
                                        setMessages((prevMessages) => prevMessages.filter(msg => !msg.temp));
                                    }
                                }
                            }
                        } else if (data.error) {
                            setMessages((prevMessages) =>
                                prevMessages.map((msg) =>
                                    msg.id === tempBotMsgId ? { ...msg, text: `❌ Error: ${data.error}`, streaming: false } : msg
                                )
                            );
                            break;
                        }
                        } catch (e: any) {
                            console.error("Error parsing stream chunk:", e);
                            console.error("Failed string was:", eventString);
                            console.error("Error message:", e.message);
                            // Don't throw, just skip this chunk
                        }
                    }
                }
            }

            setMessages((prevMessages) =>
                prevMessages.map((msg) =>
                    msg.id === tempBotMsgId && msg.streaming ? { ...msg, streaming: false } : msg
                )
            );

        } catch (err: any) {
            setMessages((prev) => [
                ...prev,
                { role: "bot", text: `❌ Error: ${err.message}` },
            ]);
        } finally {
            setLoading(false);
        }
    }

    const confirmAction = (confirmed: boolean) => {
        setIsConfirmModalOpen(false);
        if (confirmed && actionToConfirm) {
            executeAction(actionToConfirm);
        } else {
            setMessages((prev) => [...prev, { role: "bot", text: "AI action cancelled by user." }]);
        }
        setActionToConfirm(null);
    };

    function executeAction(action: { type: string; [key: string]: any }) {
        console.log("Executing action:", action);
        let actionResult = { success: false, message: "No action performed." };

        switch (action.type) {
            case "click":
                actionResult = handleClick(action.selector);
                if (!actionResult.success) {
                    setMessages((prev) => [...prev, { role: "bot", text: `❌ AI Action Failed: ${actionResult.message}` }]);
                } else {
                    setMessages((prev) => [...prev, { role: "bot", text: `✅ AI clicked: ${action.selector}` }]);
                }
                break;
            case "fill_form":
                actionResult = handleFillForm(action.fields);
                if (!actionResult.success) {
                    setMessages((prev) => [...prev, { role: "bot", text: `❌ AI Action Failed: Could not fill all form fields. ${JSON.stringify(actionResult.details)}` }]);
                } else {
                    setMessages((prev) => [...prev, { role: "bot", text: `✅ AI filled form fields.` }]);
                }
                break;
            default:
                console.warn("Unknown action type:", action.type);
                setMessages((prev) => [...prev, { role: "bot", text: `❌ AI Action Failed: Unknown action type "${action.type}"` }]);
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
        <div className="flex flex-col h-full bg-white text-gray-900 border-l border-gray-200 shadow-lg">
            <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-purple-50 flex justify-between items-center">
                <h4 className="text-lg font-semibold text-gray-700">AI Concierge</h4>
            </div>

            <div className="flex-1 p-4 overflow-y-auto space-y-4">
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

            {/* Action Confirmation Modal */} 
            <Transition appear show={isConfirmModalOpen} as={Fragment}>
                <Dialog as="div" className="relative z-10" onClose={() => confirmAction(false)}>
                    <Transition.Child
                        as={Fragment}
                        enter="ease-out duration-300"
                        enterFrom="opacity-0"
                        enterTo="opacity-100"
                        leave="ease-in duration-200"
                        leaveFrom="opacity-100"
                        leaveTo="opacity-0"
                    >
                        <div className="fixed inset-0 bg-black bg-opacity-25" />
                    </Transition.Child>

                    <div className="fixed inset-0 overflow-y-auto">
                        <div className="flex min-h-full items-center justify-center p-4 text-center">
                            <Transition.Child
                                as={Fragment}
                                enter="ease-out duration-300"
                                enterFrom="opacity-0 scale-95"
                                enterTo="opacity-100 scale-100"
                                leave="ease-in duration-200"
                                leaveFrom="opacity-100 scale-100"
                                leaveTo="opacity-0 scale-95"
                            >
                                <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                                    <Dialog.Title
                                        as="h3"
                                        className="text-lg font-medium leading-6 text-gray-900"
                                    >
                                        AI Wants to Perform an Action
                                    </Dialog.Title>
                                    <div className="mt-2">
                                        {actionToConfirm && actionToConfirm.type === "click" && (
                                            <p className="text-sm text-gray-500">
                                                The AI wants to click on an element with the selector: "
                                                <code className="bg-gray-100 p-1 rounded break-all">{actionToConfirm.selector}</code>
                                            </p>
                                        )}
                                        {actionToConfirm && actionToConfirm.type === "fill_form" && (
                                            <div className="text-sm text-gray-500">
                                                <p>The AI wants to fill a form with the following details:</p>
                                                <ul className="list-disc list-inside mt-2 bg-gray-100 p-2 rounded max-h-40 overflow-y-auto">
                                                    {actionToConfirm.fields.map((field: any, index: number) => (
                                                        <li key={index}>
                                                            Selector: <code className="break-all">{field.selector}</code>, Value: "
                                                            <code className="break-all">{field.value}</code>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {actionToConfirm && !["click", "fill_form"].includes(actionToConfirm.type) && (
                                            <p className="text-sm text-gray-500">
                                                Unknown action type: {actionToConfirm.type}
                                            </p>
                                        )}
                                    </div>

                                    <div className="mt-4 flex justify-end space-x-2">
                                        <button
                                            type="button"
                                            className="inline-flex justify-center rounded-md border border-transparent bg-red-100 px-4 py-2 text-sm font-medium text-red-900 hover:bg-red-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                                            onClick={() => confirmAction(false)}
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            type="button"
                                            className="inline-flex justify-center rounded-md border border-transparent bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900 hover:bg-blue-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                                            onClick={() => confirmAction(true)}
                                        >
                                            Confirm
                                        </button>
                                    </div>
                                </Dialog.Panel>
                            </Transition.Child>
                        </div>
                    </div>
                </Dialog>
            </Transition>
        </div>
    );
}
