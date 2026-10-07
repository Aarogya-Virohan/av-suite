'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, ArrowUpRight, Check, Search, SlidersHorizontal, Sparkles } from 'lucide-react';
import { ProductCard } from '../../components/platform/ProductCard';
import { marketplaceCategories, platformProducts, type MarketplaceCategory } from '../../data/products';

type SortOrder = 'recommended' | 'a-z';

export default function MarketplacePage() {
  const [category, setCategory] = useState<MarketplaceCategory>('All');
  const [query, setQuery] = useState('');
  const [sortOrder, setSortOrder] = useState<SortOrder>('recommended');
  const featuredProduct = platformProducts.find((product) => product.featured)!;
  const FeaturedIcon = featuredProduct.icon;
  const installedCount = platformProducts.filter((product) => product.status === 'installed').length;
  const availableCount = platformProducts.length - installedCount;
  const searchTerm = query.trim().toLowerCase();
  const matchingProducts = platformProducts.filter((product) => {
    const matchesCategory = category === 'All' || product.category === category;
    const matchesSearch = !searchTerm || `${product.name} ${product.category} ${product.description} ${product.metadata}`.toLowerCase().includes(searchTerm);
    return matchesCategory && matchesSearch;
  });
  const showFeatured = category === 'All' && searchTerm.length === 0;
  const sortedProducts = sortOrder === 'a-z'
    ? [...matchingProducts].sort((first, second) => first.name.localeCompare(second.name))
    : matchingProducts;

  return (
    <div className="marketplace-page">
      <section className="marketplace-heading">
        <div className="marketplace-heading-copy">
          <p className="page-kicker">AROGYA VIROHAN <span>·</span> WORKSPACE CAPABILITIES</p>
          <h1>Arogya Marketplace</h1>
          <p>Extend your workspace with clinical, operational, and intelligent capabilities.</p>
        </div>
        <div className="catalog-context" aria-label={`${installedCount} installed products and ${availableCount} available products`}>
          <span><i className="context-installed-dot" />{installedCount} installed</span>
          <span className="context-divider" />
          <span>{availableCount} available</span>
        </div>
      </section>

      <section className="catalog-controls" aria-label="Marketplace search and filters">
        <label className="catalog-search"><Search size={17} /><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search clinical tools and capabilities" aria-label="Search marketplace products" /><kbd><span>⌘</span> K</kbd></label>
        <label className="catalog-sort"><SlidersHorizontal size={15} /><span className="sr-only">Sort products</span><select value={sortOrder} onChange={(event) => setSortOrder(event.target.value as SortOrder)} aria-label="Sort products"><option value="recommended">Recommended</option><option value="a-z">Name A–Z</option></select></label>
      </section>

      <nav className="category-navigation" aria-label="Product categories">
        {marketplaceCategories.map((item) => <button type="button" key={item} className={`category-tab ${category === item ? 'active' : ''}`} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}{item === 'All' && <span>{platformProducts.length}</span>}</button>)}
      </nav>

      {showFeatured && (
        <section className="featured-capability" aria-labelledby="featured-title">
          <div className="featured-topline"><span><Sparkles size={13} /> FEATURED CAPABILITY</span><span>CLINICAL WORKFLOW</span></div>
          <div className="featured-main">
            <div className={`featured-product-icon product-icon-${featuredProduct.tone}`}><FeaturedIcon size={24} strokeWidth={1.7} /></div>
            <div className="featured-copy">
              <span className="featured-category">{featuredProduct.category}</span>
              <h2 id="featured-title">{featuredProduct.name}</h2>
              <p>{featuredProduct.description} Keep the plan connected to the rest of each patient’s care journey.</p>
              <div className="featured-benefits"><span><Check size={13} /> Goal-led programs</span><span><Check size={13} /> Connected patient context</span><span><Check size={13} /> Clear next steps</span></div>
            </div>
            <div className="featured-action">
              <span className="status-badge status-available">Available</span>
              <Link href={`/marketplace/products/${featuredProduct.slug}`} className="button button-featured">Explore capability <ArrowRight size={15} /></Link>
              <small>Designed for connected care</small>
            </div>
          </div>
          <div className="featured-index"><span>01</span><span />CARE, CONNECTED</div>
        </section>
      )}

      <section id="all-capabilities" className="capability-section" aria-labelledby="capability-heading">
        <div className="section-heading">
          <div><p className="section-kicker">BUILT AROUND THE WORK OF CARE</p><h2 id="capability-heading">{category === 'All' ? 'All capabilities' : category}</h2><p>Products work within the same workspace, with each capability serving a clear role.</p></div>
          <span className="result-count">{sortedProducts.length.toString().padStart(2, '0')} <small>CAPABILITIES</small></span>
        </div>

        {sortedProducts.length ? (
          <div className="marketplace-product-grid">
            {sortedProducts.map((product) => <ProductCard key={product.id} product={product} variant="marketplace" />)}
          </div>
        ) : (
          <div className="catalog-empty"><div className="empty-mark"><Search size={19} /></div><strong>No matching capabilities</strong><p>Try another search or category.</p><button type="button" onClick={() => { setCategory('All'); setQuery(''); }}>Clear filters</button></div>
        )}
      </section>

      <aside className="catalog-note"><span className="catalog-note-icon"><Check size={14} /></span><p><strong>One connected workspace.</strong> Products share context by design, so your team can move from patient needs to the right clinical capability.</p><Link href="/platform">Back to platform home <ArrowUpRight size={14} /></Link></aside>
    </div>
  );
}