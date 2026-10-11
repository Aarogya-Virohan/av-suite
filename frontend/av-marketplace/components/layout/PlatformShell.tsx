'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import {
  Bell,
  ChevronDown,
  Check,
  CircleHelp,
  Home,
  LayoutGrid,
  Search,
  ShoppingBag,
  type LucideIcon,
} from 'lucide-react';
import { usePlatform } from '../platform/PlatformProvider';
import { endSession } from '../../lib/api-client';
import { getProductIcon } from '../../data/products';

const platformLinks: { label: string; href: string; icon: LucideIcon }[] = [
  { label: 'Home', href: '/platform', icon: Home },
  { label: 'Marketplace', href: '/marketplace', icon: ShoppingBag },
  { label: 'Products', href: '/marketplace#all-capabilities', icon: LayoutGrid },
];

export function PlatformShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();
  const { context, loading, clear } = usePlatform();
  const [signOutError, setSignOutError] = useState<string | null>(null);
  const detailSlug = pathname.startsWith('/marketplace/products/') ? pathname.split('/').at(-1) : undefined;
  const currentProduct = context?.active_products.find((product) => product.key === detailSlug);
  const currentContext = currentProduct?.name ?? (pathname.startsWith('/marketplace') ? 'Marketplace' : 'Platform');
  const isProductDetail = pathname.startsWith('/marketplace/products/');
  const activeWorkspace = context?.active_workspace;
  const initials = context?.user.name.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase() ?? 'AV';

  async function signOut() {
    setSignOutError(null);
    try {
      await endSession();
      clear();
      router.replace('/login');
    } catch (cause) {
      setSignOutError(cause instanceof Error ? cause.message : 'Unable to sign out.');
    }
  }

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
            <summary className="rail-user" aria-label="Account menu" title={context?.user.name ?? 'Account'}><span className="profile-avatar">{initials}</span></summary>
            <div className="rail-popover account-popover">
              {context ? <><strong>{context.user.name}</strong><small>{context.user.email} · {context.active_workspace?.role}</small><button type="button" onClick={() => void signOut()}>Sign out</button>{signOutError && <small role="alert">{signOutError}</small>}</> : <><strong>{loading ? 'Loading account…' : 'Not signed in'}</strong><Link href="/login">Sign in</Link></>}
            </div>
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
                {context?.active_products.length ? <p>ACTIVE PRODUCTS</p> : null}
                {context?.active_products.map((product) => {
                  const Icon = getProductIcon(product.key) ?? LayoutGrid;
                  return <Link key={product.key} href={`/marketplace/products/${encodeURIComponent(product.key)}`}><Icon size={15} />{product.name}</Link>;
                })}
              </div>
            </details>
          </div>
          {(context?.workspaces.length ?? 0) > 1 ? (
            <details className="workspace-selector">
              <summary><span className="topbar-workspace-mark">{activeWorkspace?.name.slice(0, 2).toUpperCase() ?? 'WS'}</span><span className="workspace-name">{activeWorkspace?.name ?? 'Workspace unavailable'}</span><ChevronDown size={14} /></summary>
              <div className="rail-popover workspace-popover"><p>YOUR WORKSPACES</p>{context?.workspaces.map((workspace) => <div className={`workspace-option ${workspace.id === activeWorkspace?.id ? 'workspace-option-active' : ''}`} key={workspace.id} aria-current={workspace.id === activeWorkspace?.id ? 'true' : undefined}><span><strong>{workspace.name}</strong><small>{workspace.type} · {workspace.role}</small></span>{workspace.id === activeWorkspace?.id && <Check size={14} />}</div>)}</div>
            </details>
          ) : (
            <div className="workspace-static" aria-label="Active workspace"><span className="topbar-workspace-mark">{activeWorkspace?.name.slice(0, 2).toUpperCase() ?? 'WS'}</span><span className="workspace-name">{activeWorkspace?.name ?? (loading ? 'Loading workspace…' : 'Workspace unavailable')}</span></div>
          )}
          <label className="platform-search topbar-search" title="Platform search is not available yet"><Search size={15} /><input type="search" placeholder="Search unavailable" aria-label="Platform search unavailable" disabled /></label>
          <div className="topbar-actions">
            <button type="button" className="icon-button notification-button" aria-label="Notifications unavailable" title="Notifications are not available yet" disabled><Bell size={18} /></button>
            <span className="topbar-separator" />
            <details className="topbar-account"><summary className="profile-button" aria-label="User profile"><span className="profile-avatar">{initials}</span><span className="profile-name">{context?.user.name ?? (loading ? 'Loading…' : 'Sign in')}</span><ChevronDown size={14} /></summary><div className="rail-popover topbar-account-popover">{context ? <><strong>{context.user.name}</strong><small>{context.user.email}</small><button type="button" onClick={() => void signOut()}>Sign out</button>{signOutError && <small role="alert">{signOutError}</small>}</> : <><strong>{loading ? 'Loading account…' : 'Not signed in'}</strong><Link href="/login">Sign in</Link></>}</div></details>
          </div>
        </header>
        <main className="platform-content">{children}</main>
      </div>
    </div>
  );
}