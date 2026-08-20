'use client';

import { useEffect, useRef, useState } from 'react';

import { AttachMenu } from '@/components/chat/AttachMenu';
import { SendIcon, StopIcon } from '@/components/common/Icon';
import { validateMessage } from '@/utils/validation';

interface ChatInputProps {
  isStreaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
  /** Hides the disclaimer when the composer sits in the middle of the welcome screen. */
  showHint?: boolean;
  /** From Settings: true sends on Enter, false requires Ctrl/Cmd+Enter. */
  sendOnEnter?: boolean;
}

const MAX_TEXTAREA_HEIGHT = 200;

/** Pill-shaped composer, centred on screen while the conversation is still empty. */
export function ChatInput({
  isStreaming,
  onSend,
  onStop,
  showHint = true,
  sendOnEnter = true,
}: ChatInputProps) {
  const [value, setValue] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Grow the textarea with its content, capped at MAX_TEXTAREA_HEIGHT.
  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;

    element.style.height = 'auto';
    element.style.height = `${Math.min(element.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
  }, [value]);

  const isEmpty = value.trim().length === 0;

  const submit = () => {
    if (isStreaming) return;

    const result = validateMessage(value);
    if (!result.valid) {
      setValidationError(result.error ?? null);
      return;
    }

    setValidationError(null);
    setValue('');
    onSend(value.trim());
  };

  return (
    <form
      className="mx-auto w-full max-w-3xl"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <div className="flex items-end gap-1.5 rounded-[26px] border border-border-subtle bg-composer px-2 py-2 shadow-[var(--shadow-composer)] transition focus-within:border-text-faint">
        <AttachMenu />

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key !== 'Enter') return;

            // On: Enter sends, Shift+Enter breaks. Off: Enter breaks, Ctrl/Cmd+Enter sends.
            const shouldSend = sendOnEnter
              ? !event.shiftKey
              : event.ctrlKey || event.metaKey;

            if (shouldSend) {
              event.preventDefault();
              submit();
            }
          }}
          rows={1}
          placeholder="Hỏi bất kỳ điều gì"
          className="scroll-thin max-h-[200px] flex-1 resize-none bg-transparent px-1 py-2 text-[15px] leading-6 outline-none placeholder:text-text-faint"
          aria-label="Nội dung tin nhắn"
          aria-invalid={validationError !== null}
        />

        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            aria-label="Dừng trả lời"
            title="Dừng trả lời"
            className="mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent text-accent-contrast transition hover:opacity-90"
          >
            <StopIcon className="h-4 w-4" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={isEmpty}
            aria-label="Gửi tin nhắn"
            title="Gửi tin nhắn"
            className={[
              'mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition',
              isEmpty
                ? 'cursor-not-allowed bg-hover text-text-faint'
                : 'bg-accent text-accent-contrast hover:opacity-90',
            ].join(' ')}
          >
            <SendIcon className="h-[18px] w-[18px]" />
          </button>
        )}
      </div>

      {validationError ? (
        <p className="mt-2 text-center text-xs text-danger" role="alert">
          {validationError}
        </p>
      ) : (
        showHint && (
          <p className="mt-2 text-center text-xs text-text-faint">
            Model mã nguồn mở tự host — nội dung có thể chưa chính xác, hãy kiểm chứng lại.
          </p>
        )
      )}
    </form>
  );
}
