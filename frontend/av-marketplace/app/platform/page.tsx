import Link from 'next/link';
import { ArrowRight, ArrowUpRight, CalendarDays } from 'lucide-react';
import { ProductCard } from '../../components/platform/ProductCard';
import { platformProducts } from '../../data/products';

export default function PlatformHomePage() {
  return (
    <div className="platform-home">
      <div className="page-intro">
        <div><p className="page-kicker">TUESDAY, 7 OCTOBER 2026 <span>·</span> AROGYA PHYSIOTHERAPY CLINIC</p><h1>Arogya Virohan Platform</h1><p className="page-intro-copy">Your healthcare workspace, connected.</p></div>
        <div className="page-intro-meta"><span className="workspace-live-dot" />Workspace ready</div>
      </div>

      <section className="welcome-banner" aria-label="Welcome to your workspace">
        <div className="welcome-copy">
          <p className="welcome-kicker">YOUR WORKSPACE</p>
          <h2>Care works better<br />when it works together.</h2>
          <p>Clinical tools, patient context, and everyday work meet in one calm, connected space.</p>
          <div className="welcome-details"><span><CalendarDays size={14} /> Tuesday, 7 October</span><span className="welcome-divider" /><span>4 products available</span></div>
        </div>
        <div className="welcome-image" role="img" aria-label="Physiotherapist supporting a patient through a rehabilitation exercise">
          <div className="image-label"><span className="image-label-dot" /> Arogya Physiotherapy Clinic</div>
        </div>
        <div className="welcome-index"><span>01</span><span className="index-rule" /><span>PLATFORM HOME</span></div>
      </section>

      <section id="products" className="products-section">
        <div className="section-heading">
          <div><p className="section-kicker">AVAILABLE TO YOUR TEAM</p><h2>Your Products</h2><p>Choose a capability to continue your work.</p></div>
          <span className="product-count">04 <span>PRODUCTS</span></span>
        </div>
        <div className="product-grid">
          {platformProducts.map((product) => <ProductCard key={product.id} product={product} />)}
        </div>
      </section>

      <section id="discover" className="marketplace-banner">
        <div className="marketplace-emblem"><span /><span /><span /></div>
        <div className="marketplace-copy"><p className="section-kicker">A LARGER CARE TOOLKIT</p><h2>Marketplace</h2><p>Discover more capabilities for your workspace.</p></div>
        <div className="marketplace-detail"><span>Clinical tools, chosen for how care happens.</span><span className="marketplace-preview">PRODUCT DISCOVERY <span>·</span> COMING INTO VIEW</span></div>
        <Link href="/marketplace" className="marketplace-action" aria-label="Open Marketplace"><ArrowUpRight size={18} /></Link>
        <div className="marketplace-rule" />
      </section>

      <footer className="platform-footer"><span>AROGYA VIROHAN <i /> CARE PLATFORM</span><span>One workspace. Many ways to support recovery.</span><Link href="#products">View products <ArrowRight size={13} /></Link></footer>
    </div>
  );
}