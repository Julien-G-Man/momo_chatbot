import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import logoImage from "../assets/logo.png";
import heroIllustration from "../assets/momo_chat_hero_illustration.png";
import ctaImage from "../assets/mrcarl_and_team.jpg"; 

// --- Language Dictionary ---
const languageData = {
    en: {
        // Hero Section
        heroTitle: "Instant and Reliable MTN MoMo Customer Support",
        heroSubtitle: "Your dedicated AI assistant for quick, accurate, and secure answers to all your MoMo queries. Get help without delay.",
        ctaButton: "Start Chatting Now",
        
        // Features Section
        featuresTitle: "Why Choose MoMoChat?",
        featuresSubtitle: "Discover a simple and quick new way to access customer support information.",
        
        feature1Title: "Instant Access to Answers",
        feature1Text: "Find procedures, solutions to common issues, and account information in seconds. No more time wasted on the phone.",
        
        feature2Title: "Secure & Private",
        feature2Text: "MoMo-Chat uses a private knowledge base, ensuring all answers are accurate, relevant, and policy-compliant.",
        
        feature3Title: "24/7 Available Assistant",
        feature3Text: "Available 24 hours a day, 7 days a week, to answer frequent questions (balances, transactions, KYC), at any time.",
        
        feature4Title: "Boost Efficiency",
        feature4Text: "Reduce waiting time and resolve your queries immediately. Faster service for all MoMo users.",
        
        // CTA Block
        ctaBlockTitle: "Ready to transform your customer experience?",
        ctaBlockSubtitle: "Join thousands of MTN MoMo users already leveraging MoMo-Chat for faster and smoother information access.",
        ctaBlockButton: "Get Started Now",
        
        // Footer Links
        privacyPolicy: "Privacy Policy",
        termsOfUse: "Terms of Use",
        contactSupport: "Contact Support",
    },
    fr: {
        // Hero Section
        heroTitle: "L'Assistance Client MTN MoMo, Instantanée et Fiable",
        heroSubtitle: "Votre assistant IA dédié pour des réponses rapides, précises et sécurisées à toutes vos requêtes MoMo. Obtenez de l'aide sans attendre.",
        ctaButton: "Commencer le Chat Maintenant",
        
        // Features Section
        featuresTitle: "Pourquoi Utiliser MoMoChat ?",
        featuresSubtitle: "Découvrez une nouvelle manière simple et rapide d'accéder aux informations de support client.",
        
        feature1Title: "Accès Instantané aux Réponses",
        feature1Text: "Trouvez les procédures, les solutions aux problèmes courants et les informations de compte en quelques secondes. Plus de temps perdu au téléphone.",
        
        feature2Title: "Sécurisé & Privé",
        feature2Text: "MoMo-Chat utilise uniquement une base de connaissances privée, garantissant des réponses exactes, pertinentes et sécurisées.",
        
        feature3Title: "Assistant Disponible 24/7",
        feature3Text: "Disponible 24 heures sur 24, 7 jours sur 7, pour répondre aux questions fréquentes (soldes, transactions, KYC), à tout moment.",
        
        feature4Title: "Augmenter l'Efficacité",
        feature4Text: "Réduisez le temps d'attente et résolvez vos requêtes immédiatement. Un service plus rapide pour tous les utilisateurs MoMo.",
        
        // CTA Block
        ctaBlockTitle: "Prêt à transformer votre expérience client ?",
        ctaBlockSubtitle: "Rejoignez les milliers d'utilisateurs MTN MoMo qui profitent déjà de MoMo-Chat pour un accès à l'information plus rapide et plus fluide.",
        ctaBlockButton: "Commencer Maintenant",
        
        // Footer Links
        privacyPolicy: "Politique de Confidentialité",
        termsOfUse: "Conditions d'Utilisation",
        contactSupport: "Contacter le Support",
    }
};
// -------------------------


function LandingPage() {
    // 1. Language State: Initialize to French (fr)
    const [language, setLanguage] = useState('fr'); 
    
    // 2. Handler function to switch language
    const toggleLanguage = () => {
        setLanguage(prevLang => prevLang === 'fr' ? 'en' : 'fr');
    };

    // 3. Current translation object based on state
    const t = languageData[language];

    return (
        <div className="landing-wrapper">
        
        {/* 1. NAVBAR (Header) */}
        <nav className="navbar">
            <div className="logo">
                <Link to="/">
                    <img src={logoImage} alt="MoMo-Bot Logo" className="logo-icon" />
                </Link>
            </div>
            
            {/* Language Switcher Button (Top Right) */}
            <div className="navbar-actions">
                <button onClick={toggleLanguage} className="lang-switcher-button">
                    {language === 'fr' ? '🇺🇸 EN' : '🇫🇷 FR'}
                </button>
                {/* Removed the unused menu-icon */}
            </div>
        </nav>

        {/* 2. HERO SECTION */}
        <section className="hero-section momo-gradient-bg">
            <div className="hero-content">
            <div className="hero-text-panel">
                <h1>{t.heroTitle}</h1>
                <p>{t.heroSubtitle}</p>
                <Link to="/chat" className="cta-button primary large">{t.ctaButton}</Link>
            </div>
            <div className="hero-image-panel">
                <img src={heroIllustration} alt="Illustration IA MoMo-Bot" className="hero-illustration" />
            </div>
            </div>
        </section>
        
        <hr/>

        {/* 3. FEATURE HIGHLIGHTS SECTION */}
        <section className="section-padded feature-highlights">
            <h2>{t.featuresTitle}</h2>
            <p className="section-subtitle">{t.featuresSubtitle}</p>
            <div className="feature-grid">
            
            {/* Feature 1: Instant Knowledge Access (🤖) */}
            <div className="feature-item">
                <div className="feature-icon-wrapper">
                <span role="img" aria-label="Robot icon" style={{fontSize: '2.5rem'}}>🤖</span>
                </div>
                <h3>{t.feature1Title}</h3>
                <p>{t.feature1Text}</p>
            </div>
            
            {/* Feature 2: Secure & Private (🔐) */}
            <div className="feature-item">
                <div className="feature-icon-wrapper">
                <span role="img" aria-label="Lock icon" style={{fontSize: '2.5rem'}}>🔐</span>
                </div>
                <h3>{t.feature2Title}</h3>
                <p>{t.feature2Text}</p> 
            </div>
            
            {/* Feature 3: Always On Assistant (⚡) */}
            <div className="feature-item">
                <div className="feature-icon-wrapper">
                <span role="img" aria-label="Lightning icon" style={{fontSize: '2.5rem'}}>⚡</span>
                </div>
                <h3>{t.feature3Title}</h3>
                <p>{t.feature3Text}</p>
            </div>
            
            {/* Feature 4: Boost Efficiency (🚀) */}
            <div className="feature-item">
                <div className="feature-icon-wrapper">
                <span role="img" aria-label="Rocket icon" style={{fontSize: '2.5rem'}}>🚀</span>
                </div>
                <h3>{t.feature4Title}</h3>
                <p>{t.feature4Text}</p>
            </div>
            
            </div>
        </section>

        <hr/>

        {/* 4. CALL TO ACTION BLOCK */}
        <section className="section-padded call-to-action-block momo-dark-bg">
            <div className="cta-content">
            <div className="cta-text">
                <h2>{t.ctaBlockTitle}</h2>
                <p>{t.ctaBlockSubtitle}</p>
                <Link to="/chat" className="cta-button primary large">{t.ctaBlockButton}</Link>
            </div>
            <div className="cta-image">
                <img src={ctaImage} alt="Illustration Collaboration d'équipe" />
            </div>
            </div>
        </section>

        <hr/>

        {/* 5. FOOTER */}
        <footer className="momo-footer">
            <p>© {new Date().getFullYear()} MTN Momo. All rights reserved.</p>
            <p>
            <a href="#">{t.privacyPolicy}</a> | 
            <a href="#">{t.termsOfUse}</a> | 
            <a href="#">{t.contactSupport}</a>
            </p>
        </footer>
        </div>
    );
}

export default LandingPage;