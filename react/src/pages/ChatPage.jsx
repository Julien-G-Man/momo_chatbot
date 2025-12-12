import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import logoImage from "../assets/logo.png";

// This is used ONLY by Vercel for direct calls
const BACKEND_BASE_URL = import.meta.env.VITE_BASE_API_URL || "http://localhost:8000";

// Define the Netlify Function endpoint.
const NETLIFY_FUNCTION_URL = '/.netlify/functions/chat-proxy';

// Determine the final API URL for the fetch call.
// This checks if the app is hosted on Netlify (indicated by the presence of a specific ENV variable).
const IS_NETLIFY_DEPLOY = import.meta.env.VITE_IS_NETLIFY === 'true';

const FINAL_API_ENDPOINT = IS_NETLIFY_DEPLOY
    ? NETLIFY_FUNCTION_URL
    : `${BACKEND_BASE_URL}/chat`;

console.log("Chat API URL:", API_URL);

// Key for storing data in the browser's local storage
const STORAGE_KEY_SESSION = 'momoChatSessionId';
const STORAGE_KEY_MESSAGES = 'momoChatHistory';
const WELCOME_MESSAGE = { id: 1, text: "Yello Charismatique! Comment puis-je vous assister avec les services MTN MoMo aujourd'hui?", sender: "bot" };

function ChatPage() {
    const [sessionId, setSessionId] = useState(null);
    const [messages, setMessages] = useState([WELCOME_MESSAGE]);
    const [inputText, setInputText] = useState("");
    const [showQuickActions, setShowQuickActions] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const chatHistoryRef = useRef(null);

    // 1. Session and History Initialization
    useEffect(() => {
        const storedSessionId = localStorage.getItem(STORAGE_KEY_SESSION);
        const storedMessages = JSON.parse(localStorage.getItem(STORAGE_KEY_MESSAGES));

        if (storedSessionId && storedMessages && storedMessages.length > 0) {
            setSessionId(storedSessionId);
            setMessages(storedMessages);
        } else {
            const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
            localStorage.setItem(STORAGE_KEY_SESSION, newSessionId);
            setSessionId(newSessionId);
            setMessages([WELCOME_MESSAGE]);
        }
    }, []);

    // 2. History Persistence and Scrolling
    useEffect(() => {
        localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(messages));
        chatHistoryRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }, [messages]);


    // 3. Message Submission 
    const handleSendMessage = async (e) => {
        e.preventDefault();
        const text = inputText.trim();
        if (isLoading || text === "" || !sessionId) return;

        if (showQuickActions) {
            setShowQuickActions(false);
        }

        const newUserMessage = { id: Date.now(), text, sender: "user" };
        setMessages((prev) => [...prev, newUserMessage]);
        setInputText("");
        setIsLoading(true);

        const payload = {
            message: text,
            session_id: sessionId, 
        };

        try {
            const response = await fetch(FINAL_API_ENDPOINT, { // Use the determined endpoint
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);

            const data = await response.json();
            const botResponseText = data.response || "MomoChat couldn't find an answer. Try rephrasing.";

            const newBotMessage = { id: Date.now() + 1, text: botResponseText, sender: "bot" };
            setMessages((prev) => [...prev, newBotMessage]);
        } catch (error) {
            console.error("API Connection Error:", error);
            const errorMessage = { id: Date.now() + 2, text: "Connection error. Please try again.", sender: "bot" };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };
    
    // Handler for quick actions
    const handleQuickAction = (actionText) => {
        setInputText(actionText);
    };

    const renderMessage = (message) => {
        const messageClass = message.sender === "user" ? "user-message" : "bot-message";
        return (
            <div key={message.id} className={`message ${messageClass}`}>
                <div className="message-text">{message.text}</div>
            </div>
        );
    };

    // Show a loading screen until the session ID is initialized
    if (!sessionId) {
        return <div className="chat-app-container loading-screen">Chargement de la session...</div>;
    }

    return (
        <div className="chat-app-container">
            {/* HEADER (Reused from Landing Page structure) */}
            <header className="navbar">
                <div className="logo">
                    <Link to="/">
                        <span className="logo-icon">
                            <img src={logoImage} alt="MomoChat Logo" style={{ height: "30px" }} />
                        </span>
                    </Link>
                </div>
                <Link to="/" className="home-link">Home</Link>
            </header>

            {/* CHAT AREA - FLEX GROWS TO FILL SPACE */}
            <main className="chat-main">
                <div id="chat-history" className="chat-history">
                    {messages.map(renderMessage)}
                    <div ref={chatHistoryRef} />
                    {isLoading && (
                        <div id="typing-indicator" className="typing-indicator">
                            <span></span><span></span><span></span>
                        </div>
                    )}
                </div>
            </main>

            {/* INPUT WRAPPER - FIXED AT THE BOTTOM */}
            <div className="chat-input-area-wrapper">
                
                {/* 1. QUICK ACTIONS / KB SUGGESTIONS */}
                {showQuickActions && (
                  <div className="quick-actions">
                      <button className="quick-action-button" type="button" onClick={() => handleQuickAction("Qu’est-ce que MoMo Advance (Avance avec MoMo) et comment l’utiliser?")}>
                          Avance Avec MOMO
                      </button>
                      <button className="quick-action-button" type="button" onClick={() => handleQuickAction("Comment puis-je emprunter de l'argent avec MoMo XtraCash?")}>
                          XtraCash
                      </button>
                      <button className="quick-action-button" type="button" onClick={() => handleQuickAction("Comment envoyer de l’argent avec MoMo?")}>
                          Transfert
                      </button>
                  </div>
                )}

                {/* 2. MAIN INPUT FORM */}
                <form onSubmit={handleSendMessage} className="chat-input-area">
                    <input
                        type="text"
                        placeholder="Ask MoMOChat..."
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        disabled={isLoading}
                        autoComplete="off"
                    />
                    <button
                        className="cta-button primary"
                        type="submit"
                        disabled={isLoading || inputText.trim() === ""}
                    >
                        <span className="send-icon">➤</span>
                    </button>
                </form>
            </div>
        </div>
    );
}

export default ChatPage;