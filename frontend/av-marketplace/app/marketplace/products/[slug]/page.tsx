'use client';

import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  Compass,
  Layers3,
  RefreshCw,
} from 'lucide-react';

import { usePlatform } from '../../../../components/platform/PlatformProvider';
import { ApiError, disableProduct, enableProduct, getInstalledProducts, getMarketplaceProducts, installProduct } from '../../../../lib/api-client';
import { getProductWorksWith, presentMarketplaceProduct, type PlatformProduct } from '../../../../data/products';

interface ProductDetailPageProps {
  params: Promise<{ slug: string }>;
}

export default function ProductDetailPage({ params }: ProductDetailPageProps) {
  const { slug } = use(params);
  return <ProductDetail productKey={slug} />;
}

function ProductDetail({ productKey }: { productKey: string }) {
  const { context, refresh } = usePlatform();
  const [product, setProduct] = useState<PlatformProduct | null>(null);
  const [catalog, setCatalog] = useState<PlatformProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError(null);
    Promise.all([getMarketplaceProducts(), getInstalledProducts()])
      .then(([products, installed]) => {
        if (!current) return;
        const installedByKey = new Map(installed.map((item) => [item.product_key, item]));
        const mapped = products.map((item) => presentMarketplaceProduct(
          item,
          installedByKey.get(item.product_key),
        ));
        setCatalog(mapped);
        setProduct(mapped.find((item) => item.key === productKey) ?? null);
      })
      .catch((cause: unknown) => {
        if (!current) return;
        setError(cause instanceof ApiError
          ? cause
          : new ApiError(503, 'Product details could not be loaded. Try again shortly.'));
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => { current = false; };
  }, [productKey, reloadKey]);

  async function runAction(action: 'install' | 'enable' | 'disable') {
    if (!product || pending) return;
    setPending(true);
    setActionError(null);
    setNotice(null);
    try {
      if (action === 'install') await installProduct(product.key);
      if (action === 'enable') await enableProduct(product.key);
      if (action === 'disable') await disableProduct(product.key);
      setNotice(action === 'install' ? 'Product installed.' : `Product ${action}d.`);
      setReloadKey((value) => value + 1);
      void refresh();
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : 'The product action failed. Try again.');
    } finally {
      setPending(false);
    }
  }

  if (loading) {
    return <section className="platform-state" aria-live="polite"><span className="state-indicator" /><h1>Loading product</h1><p>Checking the current workspace catalog.</p></section>;
  }

  if (error) {
    return (
      <section className="platform-state" role="alert">
        <h1>{error.status === 401 ? 'Sign in to view this product' : 'Product unavailable'}</h1>
        <p>{error.message}</p>
        {error.status === 401
          ? <Link className="button button-featured" href="/login">Sign in <ArrowRight size={14} /></Link>
          : <button className="button button-featured" type="button" onClick={() => setReloadKey((value) => value + 1)}>Try again <RefreshCw size={14} /></button>}
      </section>
    );
  }

  if (!product) {
    return (
      <section className="platform-state" role="status">
        <p className="section-kicker">PRODUCT NOT FOUND</p>
        <h1>This product is not in the workspace catalog</h1>
        <p>The product may be unavailable or the link may be out of date.</p>
        <Link className="button button-featured" href="/marketplace">Back to Marketplace <ArrowLeft size={14} /></Link>
      </section>
    );
  }

  const Icon = product.icon;
  const relatedKeys = getProductWorksWith(product.key);
  const connectedProducts = catalog.filter((item) => relatedKeys.includes(item.key));
  const capabilities = context?.capabilities ?? [];
  const statusLabel = !product.eligible
    ? 'Not eligible for this workspace'
    : !product.installed
      ? 'Available for your workspace'
      : product.enabled
        ? 'Installed and enabled'
        : 'Installed but disabled';
  const statusClass = product.installed
    ? product.enabled ? 'status-installed' : 'status-disabled'
    : 'status-available';

  return (
    <div className="product-detail-page">
      <nav className="detail-breadcrumb" aria-label="Breadcrumb"><Link href="/platform">Platform</Link><ChevronRight size={13} /><Link href="/marketplace">Marketplace</Link><ChevronRight size={13} /><span>{product.name}</span></nav>

      <section className={`detail-hero detail-hero-${product.tone}`}>
        <div className="detail-hero-copy">
          <p className="page-kicker">AROGYA VIROHAN <span>·</span> {product.category.toUpperCase()} CAPABILITY</p>
          <div className="detail-title-row"><span className={`detail-product-icon product-icon-${product.tone}`}><Icon size={24} strokeWidth={1.7} /></span><h1>{product.name}</h1></div>
          <p className="detail-tagline">{product.description}</p>
          <div className="detail-status-row"><span className={`status-badge ${statusClass}`}><span />{statusLabel}</span><span>{product.metadata}</span></div>
          <div className="detail-actions">
            {!product.installed ? (
              <button type="button" className="button button-detail-primary" disabled={pending || !product.eligible} onClick={() => void runAction('install')}>
                <span>{pending ? 'Installing…' : product.eligible ? 'Install' : 'Unavailable'}</span><ArrowRight size={15} />
              </button>
            ) : (
              <button type="button" className="button button-detail-primary" disabled title="The product application is not connected yet.">
                <span>Open Product</span><ArrowUpRight size={15} />
              </button>
            )}
            {product.installed && (product.enabled
              ? <button type="button" className="button button-detail-secondary" disabled={pending} onClick={() => void runAction('disable')}>{pending ? 'Disabling…' : 'Disable'}</button>
              : <button type="button" className="button button-detail-secondary" disabled={pending || !product.eligible} onClick={() => void runAction('enable')}>{pending ? 'Enabling…' : 'Enable'}</button>)}
            <Link href="/marketplace" className="button button-detail-secondary"><ArrowLeft size={14} /> Back to Marketplace</Link>
          </div>
          {actionError && <p className="form-error" role="alert">{actionError}</p>}
          {notice && <p className="action-success" role="status">{notice}</p>}
        </div>
        <div className="detail-hero-aside">
          <span className="detail-aside-kicker">PART OF YOUR CARE ECOSYSTEM</span>
          <div className="ecosystem-orbit" aria-label="Arogya Virohan connected product ecosystem">
            <span className="orbit-line orbit-line-one" /><span className="orbit-line orbit-line-two" /><span className="orbit-line orbit-line-three" />
            <span className="orbit-node orbit-node-current"><Icon size={20} /></span>
            <span className="orbit-node orbit-node-one"><Compass size={15} /></span>
            <span className="orbit-node orbit-node-two"><Layers3 size={15} /></span>
            <span className="orbit-node orbit-node-three"><Check size={15} /></span>
            <span className="orbit-center">AV</span>
          </div>
          <span className="detail-aside-caption">Shared patient context<br />across connected products</span>
        </div>
      </section>

      <div className="detail-content-grid">
        <section className="detail-panel overview-panel" aria-labelledby="overview-heading">
          <div className="detail-section-heading"><span className="section-icon"><Compass size={16} /></span><div><p className="section-kicker">OVERVIEW</p><h2 id="overview-heading">A capability within the platform</h2></div></div>
          <p>{product.description}</p>
          <div className="overview-context"><span><Check size={14} /></span><span><strong>Shared workspace context</strong><small>Product access is provided by the active workspace.</small></span></div>
        </section>

        <section className="detail-panel capabilities-panel" id="capabilities" aria-labelledby="capabilities-heading">
          <div className="detail-section-heading"><span className="section-icon"><Layers3 size={16} /></span><div><p className="section-kicker">WORKSPACE ACCESS</p><h2 id="capabilities-heading">Available capabilities</h2></div></div>
          {capabilities.length > 0 ? (
            <div className="capability-list">
              {capabilities.slice(0, 8).map((capability, index) => <div className="capability-row" key={capability}><span className="capability-number">{String(index + 1).padStart(2, '0')}</span><span>{capability}</span><Check size={14} /></div>)}
              {capabilities.length > 8 && <p className="capability-more">And {capabilities.length - 8} more available to this workspace.</p>}
            </div>
          ) : (
            <p className="detail-empty">No capabilities are currently enabled for this workspace.</p>
          )}
        </section>
      </div>

      <section className="works-with-section" aria-labelledby="works-with-heading">
        <div className="section-heading"><div><p className="section-kicker">A CONNECTED CARE WORKSPACE</p><h2 id="works-with-heading">Works with</h2><p>Related product presentation for the care journey.</p></div><Link href="/marketplace" className="text-link">Explore all capabilities <ArrowRight size={14} /></Link></div>
        <div className="related-product-grid">
          {connectedProducts.map((related) => {
            const RelatedIcon = related.icon;
            return <Link className="related-product-card" key={related.key} href={`/marketplace/products/${encodeURIComponent(related.key)}`}><span className={`product-icon product-icon-${related.tone}`}><RelatedIcon size={18} /></span><span className="related-product-copy"><small>{related.category}</small><strong>{related.name}</strong><span>{related.description}</span></span><ArrowUpRight className="related-arrow" size={16} /></Link>;
          })}
        </div>
      </section>
    </div>
  );
}