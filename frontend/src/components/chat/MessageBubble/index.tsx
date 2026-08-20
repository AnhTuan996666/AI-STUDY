'use client';

import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { SparkIcon } from '@/components/common/Icon';
import { Spinner } from '@/components/common/Spinner';

import type { ChatMessage } from '@/types/chat';

interface MessageBubbleProps {
  message: ChatMessage;
}

/** One turn: user text in a right-aligned pill, assistant reply as plain full-width text, like ChatGPT. */
export const MessageBubble = memo(function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isEmptyStreaming = message.isStreaming && message.content.length === 0;

  if (isUser) {
    return (
      <article className="flex justify-end">
        <div className="max-w-[75%] rounded-3xl bg-bubble px-5 py-2.5 text-[15px] whitespace-pre-wrap">
          {message.content}
        </div>
      </article>
    );
  }

  return (
    <article className="flex gap-3">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border-subtle">
        <SparkIcon className="h-3.5 w-3.5 text-text-muted" />
      </span>

      <div className="min-w-0 flex-1 pt-0.5 text-[15px]">
        {isEmptyStreaming ? (
          <Spinner label="AI đang soạn câu trả lời" />
        ) : (
          <div className={`markdown-body ${message.isStreaming ? 'streaming-caret' : ''}`}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        )}

        {message.error && <p className="mt-2 text-sm text-danger">⚠ {message.error}</p>}
      </div>
    </article>
  );
});
