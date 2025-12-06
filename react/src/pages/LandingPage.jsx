import React from 'react';
import { Link } from 'react-router-dom';
import logoImage from "../assets/logo.png";
import heroIllustration from "../assets/momo_chat_hero_illustration.png";
import iconInstant from "../assets/icon_instant.svg";
import iconSecure from "../assets/icon_secure.svg";
import momoTeamIllustration from "../assets/momo_team_illustration.jpg";
import momoUse from "../assets/momo_user.png";
import ctaImage from "../assets/mrcarl_and_team.jpg";


function LandingPage() {
  return (
    <div className="landing-wrapper">
      
      {/* 1. NAVBAR (Header) */}
      <nav className="navbar">
        <div className="logo">
          <Link to="/">
            {/* Use imported logoImage */}
            <img src={logoImage} alt="MomoChat Logo" className="logo-icon" />
            {/* Note: Removed the empty <h1> tag from the original HTML */}
          </Link>
        </div>
        <div className="menu-icon">&#9776;</div>
      </nav>

      {/* 2. HERO SECTION */}
      <section className="hero-section momo-gradient-bg">
        <div className="hero-content">
          <div className="hero-text-panel">
            <h1>Unlock Instant Knowledge with MomoChat AI</h1>
            <p>Your dedicated AI assistant for quick, accurate, and secure answers to all internal MTN Momo queries. Streamline workflows and empower your team.</p>
            {/* Changed <a> to <Link> and 'chat.html' to '/chat' */}
            <Link to="/chat" className="cta-button primary large">Start Chatting Now</Link>
          </div>
          <div className="hero-image-panel">
            {/* Use imported heroIllustration */}
            <img src={heroIllustration} alt="MomoChat AI illustration" className="hero-illustration" />
          </div>
        </div>
      </section>
      
      <hr/>

      {/* 3. FEATURE HIGHLIGHTS SECTION */}
      <section className="section-padded feature-highlights">
        <h2>Why Choose MomoChat?</h2>
        <p className="section-subtitle">Experience a new way to access critical information and boost productivity.</p>
        <div className="feature-grid">
          
          {/* Feature 1: Instant Knowledge Access */}
          <div className="feature-item">
            <div className="feature-icon-wrapper">
              <img src={iconInstant} alt="Instant Access Icon" />
            </div>
            <h3>Instant Knowledge Access</h3>
            <p>Find policies, procedures, and internal data in seconds. No more searching through endless documents or email chains.</p>
          </div>
          
          {/* Feature 2: Secure & Internal */}
          <div className="feature-item">
            <div className="feature-icon-wrapper">
              <img src={iconSecure} alt="Secure Internal Icon" />
            </div>
            <h3>Secure & Internal</h3>
            <p>MomoChat uses <strong>only</strong> our private knowledge base, ensuring all answers are accurate, relevant, and secure.</p>
          </div>
          
          {/* Feature 3: Always On Assistant */}
          <div className="feature-item">
            <div className="feature-icon-wrapper">
              <img src={momoTeamIllustration} alt="24/7 Assistant Icon" />
            </div>
            <h3>Always On Assistant</h3>
            <p>Available 24/7 to answer common HR, IT, and operational queries, allowing teams to focus on high-value tasks.</p>
          </div>
          
          {/* Feature 4: Boost Efficiency */}
          <div className="feature-item">
            <div className="feature-icon-wrapper">
              <img src={momoUse} alt="Efficiency Icon" />
            </div>
            <h3>Boost Efficiency</h3>
            <p>Reduce time spent on routine information retrieval, freeing up your team for strategic initiatives and innovation.</p>
          </div>
          
        </div>
      </section>

      <hr/>

      {/* 4. CALL TO ACTION BLOCK */}
      <section className="section-padded call-to-action-block momo-dark-bg">
        <div className="cta-content">
          <div className="cta-text">
            <h2>Ready to Transform Your Team's Productivity?</h2>
            <p>Join other MTN Momo teams who are already leveraging MomoChat for faster information access and streamlined operations.</p>
            {/* Changed <a> to <Link> and 'chat.html' to '/chat' */}
            <Link to="/chat" className="cta-button primary large">Get Started</Link>
          </div>
          <div className="cta-image">
            {/* Use imported ctaImage */}
            <img src={ctaImage} alt="Team Collaboration Illustration" />
          </div>
        </div>
      </section>

      <hr/>

      {/* 5. FOOTER */}
      <footer className="momo-footer">
        <p>© {new Date().getFullYear()} MTN Momo. All rights reserved.</p>
        <p>
          <a href="#">Privacy Policy</a> | 
          <a href="#">Terms of Use</a> | 
          <a href="#">Contact Support</a>
        </p>
      </footer>
    </div>
  );
}

export default LandingPage;