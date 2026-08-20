'use client';

import dynamic from 'next/dynamic';

/** Client-only: the store reads document.cookie on init, which does not exist during SSR. */
const ChatContainerImpl = dynamic(
  () => import('@/components/chat/ChatContainer/ChatContainer').then((mod) => mod.ChatContainer),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-dvh items-center justify-center text-sm text-text-muted">
        Đang tải giao diện chat…
      </div>
    ),
  },
);

export function ChatContainer() {
  return <ChatContainerImpl />;
}
