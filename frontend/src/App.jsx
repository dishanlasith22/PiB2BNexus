import React from "react";
import { ArrowRight, Boxes, Store, Truck, ShieldCheck, Globe2, CircleCheck } from "lucide-react";

const roles = [
  { icon: Store, title: "Shop Owner", text: "Run your shop, manage branches, sell products and track stock." },
  { icon: Truck, title: "Dealer", text: "Share your catalogue, deliver stock and follow settlements." },
  { icon: Boxes, title: "Customer", text: "Discover shops, scan bills, pay with Pi and collect rewards." }
];

export default function App() {
  return (
    <main className="page-shell">
      <nav className="nav">
        <a className="brand" href="/" aria-label="PIB2BNexus home">
          <span className="brand-mark">π</span><span>PIB2B<span className="brand-accent">NEXUS</span></span>
        </a>
        <div className="nav-right"><span className="status-dot" /> Development Preview</div>
      </nav>

      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><Globe2 size={15} /> PI-POWERED COMMERCE NETWORK</div>
          <h1>One network.<br /><span>Every business</span><br />connected.</h1>
          <p className="hero-lede">A smarter way for dealers, shops and customers to connect, trade and grow with Pi.</p>
          <div className="hero-actions">
            <a className="primary-btn" href="#portals">Explore the platform <ArrowRight size={17} /></a>
            <span className="secure-note"><ShieldCheck size={16} /> Built for trusted commerce</span>
          </div>
        </div>
        <div className="hero-panel">
          <div className="panel-glow" />
          <div className="orbit orbit-one" /><div className="orbit orbit-two" />
          <div className="core-logo">π</div>
          <div className="orbit-label label-top">DEALERS</div>
          <div className="orbit-label label-right">SHOPS</div>
          <div className="orbit-label label-bottom">CUSTOMERS</div>
          <div className="connection-line line-a" /><div className="connection-line line-b" /><div className="connection-line line-c" />
          <div className="panel-caption"><span className="live-pulse" /> Connected commerce ecosystem</div>
        </div>
      </section>

      <section className="portals" id="portals">
        <div className="section-heading">
          <div><div className="eyebrow">THE PIB2BNEXUS ECOSYSTEM</div><h2>Choose your workspace</h2></div>
          <p>One platform, designed around the way you do business.</p>
        </div>
        <div className="role-grid">
          {roles.map(({icon: Icon, title, text}, index) => (
            <article className="role-card" key={title}>
              <div className="role-icon"><Icon size={22} /></div>
              <div className="role-number">0{index + 1}</div>
              <h3>{title}</h3><p>{text}</p>
              <span className="card-link">Workspace preview <ArrowRight size={15} /></span>
            </article>
          ))}
        </div>
      </section>

      <section className="login-strip">
        <div className="login-symbol">π</div>
        <div><h3>Pi Network sign-in</h3><p>Secure Pi authentication is being connected to this new web experience.</p></div>
        <span className="integration-state"><CircleCheck size={15} /> Integration in progress</span>
      </section>

      <footer><span>© {new Date().getFullYear()} PIB2BNexus</span><span>Connecting commerce with Pi</span></footer>
    </main>
  );
}