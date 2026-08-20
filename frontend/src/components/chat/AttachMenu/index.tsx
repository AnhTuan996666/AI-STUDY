'use client';

import { useEffect, useRef, useState } from 'react';

import {
  GlobeIcon,
  ImageIcon,
  LibraryIcon,
  PaperclipIcon,
  PlusIcon,
  ResearchIcon,
} from '@/components/common/Icon';
import { IconButton } from '@/components/common/IconButton';

import type { ComponentType } from 'react';

interface MenuItem {
  label: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
}

/** No feature behind these yet: kept looking enabled with a "Sắp có" tag rather than greyed out. */
const ITEMS: MenuItem[] = [
  { label: 'Thêm ảnh & tệp', description: 'Tải lên từ máy', icon: PaperclipIcon },
  { label: 'Tìm trên web', description: 'Lấy tin tức mới nhất', icon: GlobeIcon },
  { label: 'Tạo ảnh', description: 'Hình dung mọi ý tưởng', icon: ImageIcon },
  { label: 'Nghiên cứu sâu', description: 'Nhận báo cáo chi tiết', icon: ResearchIcon },
  { label: 'Thêm từ thư viện', description: 'Duyệt và tìm tệp của bạn', icon: LibraryIcon },
];

/** The "+" button left of the composer; opens the attachment and tools menu. */
export function AttachMenu() {
  const [isOpen, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click or Esc, the behaviour users expect from any popover.
  useEffect(() => {
    if (!isOpen) return;

    const onPointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };

    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);

    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [isOpen]);

  return (
    <div ref={containerRef} className="relative mb-0.5 shrink-0">
      <IconButton
        label="Thêm nội dung và công cụ"
        aria-expanded={isOpen}
        aria-haspopup="menu"
        onClick={() => setOpen((open) => !open)}
        className={isOpen ? 'bg-hover text-text-primary' : ''}
      >
        <PlusIcon className="h-5 w-5" />
      </IconButton>

      {isOpen && (
        <div
          role="menu"
          className="absolute bottom-full left-0 z-30 mb-2 w-[330px] rounded-2xl border border-border-subtle bg-composer p-1.5 shadow-[var(--shadow-popover)]"
        >
          {ITEMS.map(({ label, description, icon: Icon }) => (
            <button
              key={label}
              type="button"
              role="menuitem"
              aria-disabled="true"
              title="Sắp có"
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition hover:bg-hover"
            >
              <Icon className="h-[18px] w-[18px] shrink-0" />
              <span className="min-w-0 flex-1 truncate">
                <span className="text-sm">{label}</span>
                <span className="ml-2 text-xs text-text-faint">{description}</span>
              </span>
              <span className="shrink-0 pl-2 text-xs text-text-faint">Sắp có</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
