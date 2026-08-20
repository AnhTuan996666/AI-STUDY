'use client';

import { useEffect, useRef } from 'react';

import { CloseIcon } from '@/components/common/Icon';
import { IconButton } from '@/components/common/IconButton';

import type { ReactNode } from 'react';

interface ModalProps {
  title: string;
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  /** Wider, for the settings panel with many rows. */
  size?: 'sm' | 'md';
}

const SIZE_CLASS = {
  sm: 'max-w-[420px]',
  md: 'max-w-[600px]',
} as const;

/** Overlay dialog; closes on Esc, backdrop click, or the close button. */
export function Modal({ title, isOpen, onClose, children, size = 'sm' }: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };

    document.addEventListener('keydown', onKeyDown);

    // Lock background scrolling so the page behind the overlay cannot scroll.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    panelRef.current?.focus();

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onMouseDown={(event) => {
        // Close only on a real backdrop press, not when a drag ends outside the panel.
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={[
          'max-h-[85dvh] w-full overflow-y-auto rounded-2xl bg-bg outline-none',
          'shadow-[var(--shadow-popover)]',
          SIZE_CLASS[size],
        ].join(' ')}
      >
        <div className="flex items-center justify-between border-b border-border-subtle px-5 py-3.5">
          <h2 className="text-base font-semibold">{title}</h2>
          <IconButton label="Đóng" onClick={onClose}>
            <CloseIcon className="h-[18px] w-[18px]" />
          </IconButton>
        </div>

        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}
