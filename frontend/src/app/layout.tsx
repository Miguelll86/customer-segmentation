import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Customer Segmentation & Marketing AI',
  description: 'Dashboard segmentazione clienti e campagne marketing',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="it">
      <body className="antialiased">{children}</body>
    </html>
  );
}
