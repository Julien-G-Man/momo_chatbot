import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import logoImage from "../assets/logo.png";

const BACKEND_BASE_URL = import.meta.env.VITE_BASE_API_URL || "http://localhost:8000";
const API_URL = `${BACKEND_BASE_URL}/chat`;
console.log("Chat API URL:", API_URL);

function ChatPage() {
    const [messages, setMessages] = useState([
        { id: 1, text: "Yello Charismatique! Comment puis-je vous assister avec les services MTN MoMo aujourd'hui?", sender: "bot" },
    ]);
    const [inputText, setInputText] = useState("");
    const [showQuickActions, setShowQuickActions] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const chatHistoryRef = useRef(null);

    useEffect(() => {
        // Scroll to the latest message whenever messages change
        chatHistoryRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }, [messages]);

    const handleSendMessage = async (e) => {
        e.preventDefault();
        const text = inputText.trim();
        if (isLoading || text === "") return;

        if (showQuickActions) {
          setShowQuickActions(false);
        }

        const newUserMessage = { id: Date.now(), text, sender: "user" };
        setMessages((prev) => [...prev, newUserMessage]);
        setInputText("");
        setIsLoading(true);

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text }),
            });

            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);

            const data = await response.json();
            const botResponseText = data.response || "MomoChat couldn't find an answer. Try rephrasing.";

            const newBotMessage = { id: Date.now() + 1, text: botResponseText, sender: "bot" };
            setMessages((prev) => [...prev, newBotMessage]);
        } catch (error) {
            console.error("API Connection Error:", error);
            const errorMessage = { id: Date.now() + 2, text: "Connection error. Please check your FastAPI server.", sender: "bot" };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };
    
    // Handler for quick actions (to populate the input field)
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
                      <button className="quick-action-button" type="button" onClick={() => handleQuickAction("Comment puis-je obtenir un prêt avec XtraCash par MoMo?")}>
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