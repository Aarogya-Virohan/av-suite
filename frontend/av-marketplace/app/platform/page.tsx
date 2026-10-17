'use client';

import Link from 'next/link';
import { ArrowRight, ArrowUpRight, CalendarDays, RefreshCw } from 'lucide-react';
import { usePlatform } from '../../components/platform/PlatformProvider';
import { ProductCard } from '../../components/platform/ProductCard';
import { presentActiveProduct } from '../../data/products';

export default function PlatformHomePage() {
  const { context, loading, error, refresh } = usePlatform();

  if (loading) {
    return <section className="platform-state" aria-live="polite"><span className="state-indicator" /><h1>Connecting to your workspace</h1><p>Loading your platform context and available products.</p></section>;
  }

  if (!context || error) {
    return (
      <section className="platform-state" role="alert">
        <h1>{error?.status === 401 ? 'Sign in to continue' : 'Workspace unavailable'}</h1>
        <p>{error?.message ?? 'Your platform context could not be loaded.'}</p>
        {error?.status === 401
          ? <Link className="button button-featured" href="/login">Sign in <ArrowRight size={14} /></Link>
          : <button className="button button-featured" type="button" onClick={() => void refresh()}>Try again <RefreshCw size={14} /></button>}
      </section>
    );
  }

  const products = context.active_products.map(presentActiveProduct);
  const workspaceName = context.active_workspace?.name ?? 'Your workspace';

  return (
    <div className="platform-home">
      <div className="page-intro">
        <div><p className="page-kicker">PLATFORM WORKSPACE <span>·</span> {workspaceName.toUpperCase()}</p><h1>Arogya Virohan Platform</h1><p className="page-intro-copy">Your healthcare workspace, connected.</p></div>
        <div className="page-intro-meta"><span className="workspace-live-dot" />Workspace ready</div>
      </div>

      <section className="welcome-banner" aria-label="Welcome to your workspace">
        <div className="welcome-copy">
          <p className="welcome-kicker">YOUR WORKSPACE</p>
          <h2>Care works better<br />when it works together.</h2>
          <p>Clinical tools, patient context, and everyday work meet in one calm, connected space.</p>
          <div className="welcome-details"><span><CalendarDays size={14} /> {workspaceName}</span><span className="welcome-divider" /><span>{products.length} enabled products</span><span className="welcome-divider" /><span>{context.capabilities.length} capabilities</span></div>
        </div>
        <div className="welcome-image" role="img" aria-label="Physiotherapist supporting a patient through a rehabilitation exercise">
          <div className="image-label"><span className="image-label-dot" /> {workspaceName}</div>
        </div>
        <div className="welcome-index"><span>01</span><span className="index-rule" /><span>PLATFORM HOME</span></div>
      </section>

      <section id="products" className="products-section">
        <div className="section-heading">
          <div><p className="section-kicker">AVAILABLE TO YOUR TEAM</p><h2>Your Products</h2><p>Enabled products and capabilities for this workspace.</p></div>
          <span className="product-count">{products.length.toString().padStart(2, '0')} <span>PRODUCTS</span></span>
        </div>
        {products.length > 0 ? (
          <div className="product-grid">
            {products.map((product) => <ProductCard key={product.key} product={product} />)}
          </div>
        ) : (
          <div className="catalog-empty"><strong>No enabled products yet</strong><p>Browse the marketplace to add products to this workspace.</p><Link href="/marketplace" className="text-link">Explore Marketplace <ArrowUpRight size={14} /></Link></div>
        )}
      </section>

      <section id="discover" className="marketplace-banner">
        <div className="marketplace-emblem"><span /><span /><span /></div>
        <div className="marketplace-copy"><p className="section-kicker">A LARGER CARE TOOLKIT</p><h2>Marketplace</h2><p>Discover products eligible for your workspace.</p></div>
        <div className="marketplace-detail"><span>Products and capabilities available in your workspace.</span><span className="marketplace-preview">PRODUCT DISCOVERY <span>·</span> CONNECTED</span></div>
        <Link href="/marketplace" className="marketplace-action" aria-label="Open Marketplace"><ArrowUpRight size={18} /></Link>
        <div className="marketplace-rule" />
      </section>

      <footer className="platform-footer"><span>AROGYA VIROHAN <i /> CARE PLATFORM</span><span>One workspace. Many ways to support recovery.</span><Link href="#products">View products <ArrowRight size={13} /></Link></footer>
    </div>
  );
}