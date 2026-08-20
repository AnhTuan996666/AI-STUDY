'use client';

import { useEffect, useRef } from 'react';

import { MessageBubble } from '@/components/chat/MessageBubble';
import { QueueNotice } from '@/components/chat/QueueNotice';

import type { ChatMessage, QueuePlace } from '@/types/chat';

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  queue: QueuePlace | null;
}

export function MessageList({ messages, isStreaming, queue }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the bottom on new content, including each streamed token.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, queue]);

  return (
    <div className="scroll-thin flex-1 overflow-y-auto px-4">
      <div className="mx-auto flex max-w-3xl flex-col gap-7 py-6">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {queue && <QueueNotice queue={queue} />}

        {isStreaming && !queue && (
          <p className="sr-only" role="status">
            AI đang trả lời
          </p>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
