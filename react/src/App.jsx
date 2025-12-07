import React, { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import ChatPage from "./pages/ChatPage";
import { pingHealth } from "./healthPing"; 
import "./index.css";

// Main backend URL
const API_URL = import.meta.env.VITE_BASE_API_URL || "http://momobot-cg-api.onrender.com";
console.log("Using API URL: ", API_URL);

function App() {
  // Ping backend on first load
  useEffect(() => {
    pingHealth(API_URL);

    // Keep backend awake while user has the page open
    const interval = setInterval(() => {
      pingHealth(API_URL);
    }, 10 * 60 * 1000); // every 10 minutes

    return () => clearInterval(interval);
  }, []);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        {/* Pass main backend URL to ChatPage */}
        <Route path="/chat" element={<ChatPage apiUrl={API_URL} />} />
      </Routes>
    </Router>
  );
}

export default App;
