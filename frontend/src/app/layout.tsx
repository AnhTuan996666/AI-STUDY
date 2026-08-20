import type { Metadata, Viewport } from 'next';

import { StoreProvider } from '@/providers/StoreProvider';
import { THEME_STORAGE_KEY } from '@/utils/constants';

import './globals.css';

export const metadata: Metadata = {
  title: 'AI Chat',
  description: 'Chat với model AI mã nguồn mở tự host',
};

export const viewport: Viewport = {
  // Match the real page background per mode so the mobile browser chrome does not clash.
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#212121' },
  ],
  width: 'device-width',
  initialScale: 1,
};

/** Sets data-theme from the cached theme before first paint, so the page never flashes light then dark. */
const THEME_BOOTSTRAP = `(function(){try{
var t=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});
if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t);
}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />
      </head>
      <body className="h-full antialiased">
        <StoreProvider>{children}</StoreProvider>
      </body>
    </html>
  );
}
