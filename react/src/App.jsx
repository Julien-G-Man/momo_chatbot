import React, { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import ChatPage from "./pages/ChatPage";
import { pingHealth } from "./healthPing";
import "./index.css";

// Determine base backend URL depending on environment
const BASE_API_URL = import.meta.env.VITE_BASE_API_URL || "http://localhost:8000";

function App() {
  useEffect(() => {
    // Immediate Ping to wake up backend server
    pingHealth(BASE_API_URL);

    // Set the "Keep-Alive" heartbeat for every 10 minutes
    const intervalId = setInterval(() => {
      console.log("Heartbeat ping sent...");
      pingHealth(BASE_API_URL);
    }, 600000); // 10 minutes = 600,000ms

    // THE CLEANUP
    return () => {
      console.log("Cleaning up old heartbeats");
      clearInterval(intervalId);
    };
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
