import type { Metadata } from 'next';
import { PlatformShell } from '../components/layout/PlatformShell';
import { PlatformProvider } from '../components/platform/PlatformProvider';
import './globals.css';

export const metadata: Metadata = {
  title: 'Arogya Virohan Platform',
  description: 'A connected healthcare workspace for your team and clinical products.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <PlatformProvider>
          <PlatformShell>{children}</PlatformShell>
        </PlatformProvider>
      </body>
    </html>
  );
}