import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/lib/auth-context';

export const metadata: Metadata = {
  title: 'DX-Asset | Nền tảng Quản lý Vòng đời Tài sản số',
  description: 'Phần mềm Nguồn mở Quản lý Vòng đời Tài sản Doanh nghiệp (OLP 2026 - DX-OS)',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="antialiased bg-slate-50 text-slate-900 min-h-screen">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
