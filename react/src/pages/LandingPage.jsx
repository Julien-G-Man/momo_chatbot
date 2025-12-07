import React from 'react';
import { Link } from 'react-router-dom';
import logoImage from "../assets/logo.png";
import heroIllustration from "../assets/momo_chat_hero_illustration.png";
import ctaImage from "../assets/mrcarl_and_team.jpg"; 


function LandingPage() {
  // --- Text Translations ---
  const translations = {
    // Hero Section
    heroTitle: "L'Assistance Client MTN MoMo, Instantanée et Fiable",
    heroSubtitle: "Votre assistant IA dédié pour des réponses rapides, précises et sécurisées à toutes vos requêtes MoMo. Obtenez de l'aide sans attendre.",
    ctaButton: "Commencer le Chat Maintenant",
    
    // Features Section
    featuresTitle: "Pourquoi Utiliser MoMoChat ?",
    featuresSubtitle: "Découvrez une nouvelle manière simple et rapide d'accéder aux informations de service client.",
    
    // Feature Content
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
  };
  // -------------------------

  return (
    <div className="landing-wrapper">
      
      {/* 1. NAVBAR (Header) */}
      <nav className="navbar">
        <div className="logo">
          <Link to="/">
            <img src={logoImage} alt="MoMo-Bot Logo" className="logo-icon" />
          </Link>
        </div>
        <div className="menu-icon">&#9776;</div>
      </nav>

      {/* 2. HERO SECTION */}
      <section className="hero-section momo-gradient-bg">
        <div className="hero-content">
          <div className="hero-text-panel">
            <h1>{translations.heroTitle}</h1>
            <p>{translations.heroSubtitle}</p>
            <Link to="/chat" className="cta-button primary large">{translations.ctaButton}</Link>
          </div>
          <div className="hero-image-panel">
            <img src={heroIllustration} alt="Illustration IA MoMo-Bot" className="hero-illustration" />
          </div>
        </div>
      </section>
      
      <hr/>

      {/* 3. FEATURE HIGHLIGHTS SECTION */}
      <section className="section-padded feature-highlights">
        <h2>{translations.featuresTitle}</h2>
        <p className="section-subtitle">{translations.featuresSubtitle}</p>
        <div className="feature-grid">
          
          {/* Feature 1: Instant Knowledge Access (🤖) */}
          <div className="feature-item">
            <div className="feature-icon-wrapper">
              <span role="img" aria-label="Robot icon" style={{fontSize: '2.5rem'}}>🤖</span>
            </div>
            <h3>{translations.feature1Title}</h3>
            <p>{translations.feature1Text}</p>
          </div>
          
          {/* Feature 2: Secure & Private (🔐) */}
          <div className="feature-item">
            <div className="feature-icon-wrapper">
              <span role="img" aria-label="Lock icon" style={{fontSize: '2.5rem'}}>🔐</span>
            </div>
            <h3>{translations.feature2Title}</h3>
            <p>{translations.feature2Text}</p> 
          </div>
          
          {/* Feature 3: Always On Assistant (⚡) */}
          <div className="feature-item">
            <div className="feature-icon-wrapper">
              <span role="img" aria-label="Lightning icon" style={{fontSize: '2.5rem'}}>⚡</span>
            </div>
            <h3>{translations.feature3Title}</h3>
            <p>{translations.feature3Text}</p>
          </div>
          
          {/* Feature 4: Boost Efficiency (🚀) - Using a suitable new emoji */}
          <div className="feature-item">
            <div className="feature-icon-wrapper">
              <span role="img" aria-label="Rocket icon" style={{fontSize: '2.5rem'}}>🚀</span>
            </div>
            <h3>{translations.feature4Title}</h3>
            <p>{translations.feature4Text}</p>
          </div>
          
        </div>
      </section>

      <hr/>

      {/* 4. CALL TO ACTION BLOCK */}
      <section className="section-padded call-to-action-block momo-dark-bg">
        <div className="cta-content">
          <div className="cta-text">
            <h2>{translations.ctaBlockTitle}</h2>
            <p>{translations.ctaBlockSubtitle}</p>
            <Link to="/chat" className="cta-button primary large">{translations.ctaBlockButton}</Link>
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
          <a href="#">{translations.privacyPolicy}</a> | 
          <a href="#">{translations.termsOfUse}</a> | 
          <a href="#">{translations.contactSupport}</a>
        </p>
      </footer>
    </div>
  );
}

export default LandingPage;