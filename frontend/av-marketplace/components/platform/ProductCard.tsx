import Link from 'next/link';
import { ArrowUpRight, Check } from 'lucide-react';
import type { PlatformProduct } from '../../data/products';

export function ProductCard({ product, variant = 'launcher' }: { product: PlatformProduct; variant?: 'launcher' | 'marketplace' }) {
  const Icon = product.icon;
  const description = variant === 'launcher' ? product.launcherDescription ?? product.description : product.description;

  return (
    <Link href={`/marketplace/products/${product.slug}`} className={`product-card product-card-${variant}`} aria-label={`View ${product.name} details`}>
      <div className="product-card-heading">
        <span className={`product-icon product-icon-${product.tone}`}><Icon size={20} strokeWidth={1.8} /></span>
        <span className="product-category">{product.category}</span>
      </div>
      <h3>{product.name}</h3>
      <p className="product-description">{description}</p>
      <div className="product-card-footer">
        {variant === 'launcher' ? (
          <span className="product-availability"><Check size={13} />{product.availability ?? 'Available in your workspace'}</span>
        ) : (
          <span className={`product-status product-status-${product.status}`}><span />{product.status === 'installed' ? 'Installed' : 'Available'}</span>
        )}
        {variant === 'launcher' ? <span className="product-open product-open-icon"><ArrowUpRight size={17} /></span> : <span className="product-open">{product.status === 'installed' ? 'Open' : 'Install'} <ArrowUpRight size={15} /></span>}
      </div>
      <span className="sr-only">{product.metadata}</span>
    </Link>
  );
}