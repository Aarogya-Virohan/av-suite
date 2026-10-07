'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Bell,
  ChevronDown,
  CircleHelp,
  Home,
  LayoutGrid,
  Search,
  ShoppingBag,
  type LucideIcon,
} from 'lucide-react';
import { platformProducts } from '../../data/products';

const platformLinks: { label: string; href: string; icon: LucideIcon }[] = [
  { label: 'Home', href: '/platform', icon: Home },
  { label: 'Marketplace', href: '/marketplace', icon: ShoppingBag },
  { label: 'Products', href: '/marketplace#all-capabilities', icon: LayoutGrid },
];

export function PlatformShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const detailSlug = pathname.startsWith('/marketplace/products/') ? pathname.split('/').at(-1) : undefined;
  const currentProduct = platformProducts.find((product) => product.slug === detailSlug);
  const currentContext = currentProduct?.name ?? (pathname.startsWith('/marketplace') ? 'Marketplace' : 'Platform');
  const isProductDetail = pathname.startsWith('/marketplace/products/');

  return (
    <div className="av-platform">
      <aside className="platform-rail">
        <Link href="/platform" className="rail-brand" aria-label="Arogya Virohan Platform home" title="Arogya Virohan Platform">
          <span className="brand-monogram">AV</span>
        </Link>
        <span className="rail-divider" />
        <nav className="platform-navigation" aria-label="Platform navigation">
          {platformLinks.map(({ label, href, icon: Icon }) => {
            const active = label === 'Home'
              ? pathname === '/platform'
              : label === 'Products'
                ? isProductDetail
                : pathname === '/marketplace';
            return (
              <Link key={label} href={href} className={`platform-nav-link ${active ? 'active' : ''}`} aria-current={active ? 'page' : undefined} title={label}>
                <Icon size={18} strokeWidth={1.75} /><span>{label}</span>
            </Link>
            );
          })}
        </nav>
        <div className="rail-bottom">
          <a href="mailto:support@arogyavirohan.com" className="rail-utility" aria-label="Help and support" title="Help and support"><CircleHelp size={18} /><span>Help</span></a>
          <details className="rail-account">
            <summary className="rail-user" aria-label="Account menu" title="Aditi Mehta account"><span className="profile-avatar">AM</span></summary>
            <div className="rail-popover account-popover"><strong>Dr. Aditi Mehta</strong><small>Clinic administrator</small><Link href="/platform">Platform home</Link></div>
          </details>
        </div>
      </aside>

      <div className="platform-main">
        <header className="platform-topbar">
          <div className="topbar-context-wrap">
            <Link href="/platform" className="topbar-brand"><span className="brand-monogram">AV</span><span>Arogya Virohan</span></Link>
            <span className="topbar-slash">/</span>
            <details className="context-switcher">
              <summary><span>{currentContext}</span><ChevronDown size={14} /></summary>
              <div className="rail-popover context-popover">
                <p>PLATFORM</p>
                <Link href="/platform"><Home size={15} /> Platform home</Link>
                <Link href="/marketplace"><ShoppingBag size={15} /> Marketplace</Link>
                <Link href="/marketplace#all-capabilities"><LayoutGrid size={15} /> All products</Link>
                <p>PRODUCTS</p>
                {platformProducts.map((product) => {
                  const Icon = product.icon;
                  return <Link key={product.slug} href={`/marketplace/products/${product.slug}`}><Icon size={15} />{product.name}</Link>;
                })}
              </div>
            </details>
          </div>
          <details className="workspace-selector">
            <summary><span className="topbar-workspace-mark">AP</span><span className="workspace-name">Arogya Physiotherapy Clinic</span><ChevronDown size={14} /></summary>
            <div className="rail-popover workspace-popover"><p>YOUR WORKSPACE</p><strong>Arogya Physiotherapy Clinic</strong><small>Workspace context · Prototype</small><div className="workspace-option">Mehta Movement Studio</div><div className="workspace-option">Personal workspace</div></div>
          </details>
          <label className="platform-search topbar-search"><Search size={15} /><input type="search" placeholder="Search" aria-label="Search platform" /></label>
          <div className="topbar-actions">
            <button type="button" className="icon-button notification-button" aria-label="Notifications"><Bell size={18} /><i /></button>
            <span className="topbar-separator" />
            <details className="topbar-account"><summary className="profile-button" aria-label="User profile"><span className="profile-avatar">AM</span><span className="profile-name">Aditi Mehta</span><ChevronDown size={14} /></summary><div className="rail-popover topbar-account-popover"><strong>Dr. Aditi Mehta</strong><small>Clinic administrator</small><Link href="/platform">Account settings</Link></div></details>
          </div>
        </header>
        <main className="platform-content">{children}</main>
      </div>
    </div>
  );
}