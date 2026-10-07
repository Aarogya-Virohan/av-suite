import Link from 'next/link';
import { notFound } from 'next/navigation';
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleCheck,
  Compass,
  Layers3,
} from 'lucide-react';
import { platformProducts, getProductBySlug, getProductNameById } from '../../../../data/products';

export function generateStaticParams() {
  return platformProducts.map((product) => ({ slug: product.slug }));
}

export default async function ProductDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const product = getProductBySlug(slug);

  if (!product) notFound();

  const Icon = product.icon;
  const connectedProducts = product.worksWith
    .map((id) => platformProducts.find((item) => item.id === id))
    .filter((item): item is (typeof platformProducts)[number] => Boolean(item));

  return (
    <div className="product-detail-page">
      <nav className="detail-breadcrumb" aria-label="Breadcrumb"><Link href="/platform">Platform</Link><ChevronRight size={13} /><Link href="/marketplace">Marketplace</Link><ChevronRight size={13} /><span>{product.name}</span></nav>

      <section className={`detail-hero detail-hero-${product.tone}`}>
        <div className="detail-hero-copy">
          <p className="page-kicker">AROGYA VIROHAN <span>·</span> {product.category.toUpperCase()} CAPABILITY</p>
          <div className="detail-title-row"><span className={`detail-product-icon product-icon-${product.tone}`}><Icon size={24} strokeWidth={1.7} /></span><h1>{product.name}</h1></div>
          <p className="detail-tagline">{product.description}</p>
          <div className="detail-status-row"><span className={`status-badge status-${product.status}`}><span />{product.status === 'installed' ? 'Installed in your workspace' : 'Available for your workspace'}</span><span>{product.metadata}</span></div>
          <div className="detail-actions">
            {product.status === 'installed'
              ? <button type="button" className="button button-detail-primary" disabled><span>Open Product</span><ArrowUpRight size={15} /></button>
              : <button type="button" className="button button-detail-primary" disabled><span>Install</span><ArrowRight size={15} /></button>}
            <Link href="/marketplace" className="button button-detail-secondary"><ArrowLeft size={14} /> Back to Marketplace</Link>
          </div>
          <p className="prototype-note">Product actions are a preview and are not connected yet.</p>
        </div>
        <div className="detail-hero-aside">
          <span className="detail-aside-kicker">PART OF YOUR CARE ECOSYSTEM</span>
          <div className="ecosystem-orbit" aria-label="Arogya Virohan connected product ecosystem">
            <span className="orbit-line orbit-line-one" /><span className="orbit-line orbit-line-two" /><span className="orbit-line orbit-line-three" />
            <span className="orbit-node orbit-node-current"><Icon size={20} /></span>
            <span className="orbit-node orbit-node-one"><Compass size={15} /></span>
            <span className="orbit-node orbit-node-two"><Layers3 size={15} /></span>
            <span className="orbit-node orbit-node-three"><CircleCheck size={15} /></span>
            <span className="orbit-center">AV</span>
          </div>
          <span className="detail-aside-caption">Shared patient context<br />across connected products</span>
        </div>
      </section>

      <div className="detail-content-grid">
        <section className="detail-panel overview-panel" aria-labelledby="overview-heading">
          <div className="detail-section-heading"><span className="section-icon"><Compass size={16} /></span><div><p className="section-kicker">OVERVIEW</p><h2 id="overview-heading">A capability within the platform</h2></div></div>
          <p>{product.overview}</p>
          <div className="overview-context"><span><Check size={14} /></span><span><strong>Shared workspace context</strong><small>Works alongside the patient and clinical tools your team already uses.</small></span></div>
        </section>

        <section className="detail-panel capabilities-panel" id="capabilities" aria-labelledby="capabilities-heading">
          <div className="detail-section-heading"><span className="section-icon"><Layers3 size={16} /></span><div><p className="section-kicker">WHAT IT SUPPORTS</p><h2 id="capabilities-heading">Capabilities</h2></div></div>
          <div className="capability-list">
            {product.capabilities.map((capability, index) => <div className="capability-row" key={capability}><span className="capability-number">{String(index + 1).padStart(2, '0')}</span><span>{capability}</span><Check size={14} /></div>)}
          </div>
        </section>
      </div>

      <section className="works-with-section" aria-labelledby="works-with-heading">
        <div className="section-heading"><div><p className="section-kicker">A CONNECTED CARE WORKSPACE</p><h2 id="works-with-heading">Works with</h2><p>Related capabilities can share context as the patient journey moves forward.</p></div><Link href="/marketplace" className="text-link">Explore all capabilities <ArrowRight size={14} /></Link></div>
        <div className="related-product-grid">
          {connectedProducts.map((related) => {
            const RelatedIcon = related.icon;
            return <Link className="related-product-card" key={related.id} href={`/marketplace/products/${related.slug}`}><span className={`product-icon product-icon-${related.tone}`}><RelatedIcon size={18} /></span><span className="related-product-copy"><small>{related.category}</small><strong>{getProductNameById(related.id)}</strong><span>{related.description}</span></span><ArrowUpRight className="related-arrow" size={16} /></Link>;
          })}
        </div>
      </section>
    </div>
  );
}