import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import App from './App.jsx';
import ChatApp from './pages/ChatPage.jsx'; 
import LandingPage from './pages/LandingPage.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Router>
      <Routes>
        {/* The Landing Page (index.html) will be the root route */}
        <Route path="/" element={<LandingPage />} />
        {/* The Chat Page will be a separate route */}
        <Route path="/chat" element={<ChatApp />} />
      </Routes>
    </Router>
  </React.StrictMode>,
)