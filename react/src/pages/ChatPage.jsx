import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import logoImage from '../assets/logo.png';

const BACKEND_BASE_URL = import.meta.env.VITE_BASE_API_URL; 
const API_URL = `${BACKEND_BASE_URL}/chat`;

function ChatPage() {
  const [messages, setMessages] = useState([
    { id: 1, text: "Welcome to MomoChat! How can I assist you with MTN MoMo's services today?", sender: 'bot' },
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatHistoryRef = useRef(null);

  // Auto-scroll to the bottom when messages update
  useEffect(() => {
    chatHistoryRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    const text = inputText.trim();
    if (isLoading || text === '') return;

    // Add user message
    const newUserMessage = { id: Date.now(), text: text, sender: 'user' };
    setMessages(prev => [...prev, newUserMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      // Call FastAPI backend
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      const botResponseText = data.response || "MomoChat couldn't find an answer. Try rephrasing.";

      // 3. Add bot message
      const newBotMessage = { id: Date.now() + 1, text: botResponseText, sender: 'bot' };
      setMessages(prev => [...prev, newBotMessage]);

    } catch (error) {
      console.error("API Connection Error:", error);
      const errorMessage = { id: Date.now() + 2, text: "Connection error. Please check your FastAPI server.", sender: 'bot' };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const renderMessage = (message) => {
    const messageClass = message.sender === 'user' ? 'user-message' : 'bot-message';
    
    return (
      <div key={message.id} className={`message ${messageClass}`}>
        <div className="message-text">
          {message.text}
        </div>
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
              <img src={logoImage} alt="MomoChat Logo" style={{ height: '30px' }} />
            </span> 
          </Link>
        </div>
        <Link to="/" className="home-link">Home</Link>
      </header>

      {/* MAIN CHAT AREA */}
      <main className="chat-main">
        <div id="chat-history" className="chat-history">
          {messages.map(renderMessage)}
          <div ref={chatHistoryRef} /> {/* Scroll target at the bottom */}
          
          {/* TYPING INDICATOR: Visible when loading */}
          {isLoading && (
             <div id="typing-indicator" className="typing-indicator">
               <span></span><span></span><span></span>
             </div>
          )}
        </div>
      </main>

      {/* INPUT AREA */}
      <form onSubmit={handleSendMessage} className="chat-input-area">
        <input 
          type="text" 
          id="user-input" 
          placeholder="Ask your internal question..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          disabled={isLoading}
          autoComplete="off"
        />
        <button 
          id="send-button" 
          className="cta-button primary"
          type="submit"
          disabled={isLoading || inputText.trim() === ''}
        >
          <span className="send-icon">➤</span>
        </button>
      </form>

    </div>
  );
}

export default ChatPage;