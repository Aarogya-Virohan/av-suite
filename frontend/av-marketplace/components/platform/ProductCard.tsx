import Link from 'next/link';
import { ArrowUpRight, Check } from 'lucide-react';
import type { PlatformProduct } from '../../data/products';

export function ProductCard({ product, variant = 'launcher' }: { product: PlatformProduct; variant?: 'launcher' | 'marketplace' }) {
  const Icon = product.icon;
  const statusLabel = !product.eligible
    ? 'Not available for this workspace'
    : !product.installed
      ? 'Available to install'
      : product.enabled
        ? 'Installed and enabled'
        : 'Installed and disabled';

  return (
    <Link href={`/marketplace/products/${encodeURIComponent(product.key)}`} className={`product-card product-card-${variant}`} aria-label={`View ${product.name} details`}>
      <div className="product-card-heading">
        <span className={`product-icon product-icon-${product.tone}`}><Icon size={20} strokeWidth={1.8} /></span>
        <span className="product-category">{product.category}</span>
      </div>
      <h3>{product.name}</h3>
      <p className="product-description">{product.description}</p>
      <div className="product-card-footer">
        {variant === 'launcher' ? (
          <span className="product-availability"><Check size={13} />{statusLabel}</span>
        ) : (
          <span className={`product-status product-status-${product.installed ? (product.enabled ? 'installed' : 'disabled') : 'available'}`}><span />{statusLabel}</span>
        )}
        {variant === 'launcher' ? <span className="product-open product-open-icon"><ArrowUpRight size={17} /></span> : <span className="product-open">Details <ArrowUpRight size={15} /></span>}
      </div>
      <span className="sr-only">{product.metadata}</span>
    </Link>
  );
}