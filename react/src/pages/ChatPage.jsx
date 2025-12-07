import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import logoImage from "../assets/logo.png";

const BACKEND_BASE_URL = import.meta.env.VITE_BASE_API_URL || "http://localhost:8000";
const API_URL = `${BACKEND_BASE_URL}/chat`;
console.log("Chat API URL:", API_URL);

function ChatPage() {
  const [messages, setMessages] = useState([
    { id: 1, text: "Welcome to MomoChat! How can I assist you with MTN MoMo's services today?", sender: "bot" },
  ]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const chatHistoryRef = useRef(null);

  useEffect(() => {
    chatHistoryRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    const text = inputText.trim();
    if (isLoading || text === "") return;

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
      {/* HEADER */}
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

      {/* CHAT AREA */}
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

      {/* INPUT */}
      <form onSubmit={handleSendMessage} className="chat-input-area">
        <input
          type="text"
          placeholder="Ask your internal question..."
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
  );
}

export default ChatPage;
