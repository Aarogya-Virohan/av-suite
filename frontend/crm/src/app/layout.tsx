import type { Metadata } from 'next';
import './globals.css';
import { AppProviders } from '@/providers/AppProviders';
import { AuthGuard } from '@/components/auth/AuthGuard';

export const metadata: Metadata = {
  title: 'Aarogya CRM | AV Suite Clinical Platform',
  description: 'Multi-tenant practice management, patient care, and clinical CRM module for Aarogya Virohan.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-[var(--teal)] selection:text-white">
        <AppProviders>
          <AuthGuard>
            {children}
          </AuthGuard>
        </AppProviders>
      </body>
    </html>
  );
}

