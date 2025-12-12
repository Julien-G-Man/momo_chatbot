import React, { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import ChatPage from "./pages/ChatPage";
import { pingHealth } from "./healthPing";
import "./index.css";

// Determine base backend URL depending on environment
const BASE_API_URL = import.meta.env.VITE_BASE_API_URL || "http://localhost:8000";
console.log("Using backend URL:", BASE_API_URL);

function App() {
  useEffect(() => {
    // Ping backend once on load 
    pingHealth(BASE_API_URL);
  }, []);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/chat" element={<ChatPage baseApiUrl={BASE_API_URL} />} />
      </Routes>
    </Router>
  );
}

export default App;
