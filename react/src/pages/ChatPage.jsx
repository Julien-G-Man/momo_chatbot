import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import logoImage from "../assets/logo.png";

const BACKEND_BASE_URL = import.meta.env.VITE_BASE_API_URL || "http://localhost:8000";
const CHAT_API_URL = `${BACKEND_BASE_URL}/chat`;

const parseMessageWithLinks = (text) => {
    // 1. ADDED: Regex for Markdown links [Text](URL)
    const markdownLinkPattern = /\[([^\]]+)\]\((https?:\/\/[^\s)]+|www\.[^\s)]+)\)/gi;
    
    // Regex patterns for URLs and emails
    const urlPattern = /(https?:\/\/[^\s]+|www\.[^\s]+)/gi;
    const emailPattern = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/gi;

    // Check for Markdown links and replace them with anchor tags
    // We do this first so the raw URL pattern doesn't "steal" the URL from the brackets
    let lastIndex = 0;
    let parts = [];
    const markdownMatches = [...text.matchAll(markdownLinkPattern)];

    if (markdownMatches.length > 0) {
        markdownMatches.forEach((match, i) => {
            const startIndex = match.index;
            const fullMatch = match[0];
            const linkText = match[1];
            let url = match[2];

            // Add text before the markdown link
            parts.push(text.substring(lastIndex, startIndex));

            if (url.startsWith('www.')) url = 'https://' + url;

            parts.push(
                <a 
                    key={`md-${i}`} 
                    href={url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ color: '#0000EE', textDecoration: 'underline', cursor: 'pointer' }}
                >
                    {linkText}
                </a>
            );
            lastIndex = startIndex + fullMatch.length;
        });
        // Process the remainder of the string for emails/urls if needed, 
        // or just return if the AI strictly uses Markdown
        text = text.substring(lastIndex);
    }

    // Split by URLs first
    const urlMatches = [...text.matchAll(urlPattern)];
    
    if (urlMatches.length === 0) {
        // No URLs, check for emails
        const emailMatches = [...text.matchAll(emailPattern)];
        if (emailMatches.length === 0) {
            return parts.length > 0 ? [...parts, text] : text; 
        }
        
        // Process emails
        let emailLastIndex = 0;
        const emailParts = emailMatches.map((match, i) => {
            const email = match[0];
            const startIndex = match.index;
            const before = text.substring(emailLastIndex, startIndex);
            emailLastIndex = startIndex + email.length;
            
            return (
                <React.Fragment key={i}>
                    {before}
                    <a 
                        href={`mailto:${email}`} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        style={{ color: '#0000EE', textDecoration: 'underline', cursor: 'pointer' }}
                    >
                        {email}
                    </a>
                </React.Fragment>
            );
        });
        return [...parts, ...emailParts, text.substring(emailLastIndex)];
    }
    
    // Process URLs
    let urlLastIndex = 0;
    const urlParts = urlMatches.map((match, i) => {
        const url = match[0];
        const startIndex = match.index;
        const before = text.substring(urlLastIndex, startIndex);
        urlLastIndex = startIndex + url.length;
        
        let fullUrl = url;
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            fullUrl = 'https://' + url;
        }
        
        return (
            <React.Fragment key={i}>
                {before}
                <a 
                    href={fullUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ color: '#0000EE', textDecoration: 'underline', cursor: 'pointer' }}
                >
                    {url}
                </a>
            </React.Fragment>
        );
    });
    
    return [...parts, ...urlParts, text.substring(urlLastIndex)];
};

function ChatPage() {
    const [messages, setMessages] = useState([
        { id: 1, text: "Yello Charismatique! Je suis MoMoChat, l'assistant client MTN MoMo, instantanée et fiable. Comment puis-je vous assister avec les services MTN MoMo aujourd'hui?", sender: "bot" },
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
            const response = await fetch(CHAT_API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text }),
            });

            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);

            const data = await response.json();
            const botResponseText = data.response || "Oops, I couldn't find an answer. Please, try rephrasing.";

            const newBotMessage = { id: Date.now() + 1, text: botResponseText, sender: "bot" };
            setMessages((prev) => [...prev, newBotMessage]);
        } catch (error) {
            console.error("API Connection Error:", error);
            const errorMessage = { id: Date.now() + 2, text: "Oops, I'm having a little trouble connecting. Ensure you're online and try again!", sender: "bot" };
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
                <div className="message-text">
                    {message.sender === "bot" ? parseMessageWithLinks(message.text) : message.text}
                </div>
            </div>
        );
    };    

    return (
        <div className="chat-app-container">
            {/* HEADER (Reused from Landing Page structure) */}
            <header className="navbar">
                <div className="logo">
                    <Link to="/">
                        <img src={logoImage} alt="MomoChat Logo" className="logo-icon" />
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
                      <button className="quick-action-button" type="button" onClick={() => handleQuickAction(" Donne-moi un aperçu général des produits et services offerts par MTN MoMo. ")}>
                          Services MTN MoMo
                      </button>
                      <button className="quick-action-button" type="button" onClick={() => handleQuickAction(" Comment télécharger et utiliser l’application MTN MoMo App pour payer mes factures et transférer de l’argent ?")}>
                          MTN MoMo App
                      </button>
                      <button className="quick-action-button" type="button" onClick={() => handleQuickAction("Comment puis-je emprunter de l'argent avec MoMo XtraCash?")}>
                          XtraCash
                      </button>
                      <button className="quick-action-button" type="button" onClick={() => handleQuickAction("Qu’est-ce que MoMo Advance (Avance avec MoMo) et comment l’utiliser?")}>
                          Avance Avec MoMo
                      </button>
                      <button className="quick-action-button" type="button" onClick={() => handleQuickAction("Comment envoyer de l’argent à l’étranger avec MoMo via GIMACPAY ?")}>
                          Remittance
                      </button>
                  </div>
                )}

                {/* 2. MAIN INPUT FORM */}
                <form onSubmit={handleSendMessage} className="chat-input-area">
                    <input
                        type="text"
                        placeholder="Ask MoMoChat..."
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