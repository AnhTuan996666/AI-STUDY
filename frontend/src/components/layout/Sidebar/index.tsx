'use client';

import { useMemo, useState } from 'react';

import { Button } from '@/components/common/Button';
import {
  ChevronRightIcon,
  CloseIcon,
  FolderIcon,
  HelpIcon,
  ImageIcon,
  LibraryIcon,
  LogoutIcon,
  MoreIcon,
  NewChatIcon,
  PencilIcon,
  PinIcon,
  PluginIcon,
  PricingIcon,
  SearchIcon,
  SettingsIcon,
  SidebarIcon,
  SparkIcon,
  TrashIcon,
  UserIcon,
} from '@/components/common/Icon';
import { IconButton } from '@/components/common/IconButton';
import { formatRelativeTime } from '@/utils/format';
import { describeHealth } from '@/utils/health';

import type { User } from '@/types/auth';
import type { Conversation, HealthState } from '@/types/chat';
import type { ComponentType, ReactNode } from 'react';

interface SidebarProps {
  pinned: Conversation[];
  recent: Conversation[];
  activeId: string | null;
  health: HealthState;
  user: User | null;
  /** Drawer open state on small screens. */
  isOpen: boolean;
  /** Collapsed out of the layout entirely on large screens. */
  isCollapsed: boolean;
  onClose: () => void;
  onToggleCollapse: () => void;
  onNew: () => void;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onTogglePin: (id: string) => void;
  onOpenSettings: () => void;
  onLogin: () => void;
  onLogout: () => void;
}

const TONE_DOT: Record<'online' | 'muted' | 'danger', string> = {
  online: 'bg-online',
  muted: 'bg-text-faint',
  danger: 'bg-danger',
};

/** Nav items with no feature yet: left looking enabled, marked only by aria-disabled and a tooltip. */
const UPCOMING_ITEMS: { label: string; icon: ComponentType<{ className?: string }> }[] = [
  { label: 'Hình ảnh', icon: ImageIcon },
  { label: 'Thư viện', icon: LibraryIcon },
  { label: 'Tiện ích', icon: PluginIcon },
  { label: 'Dự án', icon: FolderIcon },
  { label: 'Thêm', icon: MoreIcon },
];

const ROW_CLASS = 'flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-sm transition';

/** Left column: navigation, search, conversation list, account block (FR-06, FR-07). */
export function Sidebar({
  pinned,
  recent,
  activeId,
  health,
  user,
  isOpen,
  isCollapsed,
  onClose,
  onToggleCollapse,
  onNew,
  onSelect,
  onRename,
  onDelete,
  onTogglePin,
  onOpenSettings,
  onLogin,
  onLogout,
}: SidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState('');
  const [isSearching, setSearching] = useState(false);
  const [query, setQuery] = useState('');
  const [isPinnedOpen, setPinnedOpen] = useState(true);
  const [isRecentsOpen, setRecentsOpen] = useState(true);

  const status = describeHealth(health);
  const needle = query.trim().toLowerCase();

  const visiblePinned = useMemo(() => filterByTitle(pinned, needle), [pinned, needle]);
  const visibleRecent = useMemo(() => filterByTitle(recent, needle), [recent, needle]);

  const startRename = (conversation: Conversation) => {
    setEditingId(conversation.id);
    setDraftTitle(conversation.title);
  };

  const commitRename = () => {
    if (editingId) onRename(editingId, draftTitle);
    setEditingId(null);
  };

  const closeSearch = () => {
    setSearching(false);
    setQuery('');
  };

  const renderRow = (conversation: Conversation): ReactNode =>
    editingId === conversation.id ? (
      <input
        autoFocus
        value={draftTitle}
        onChange={(event) => setDraftTitle(event.target.value)}
        onBlur={commitRename}
        onKeyDown={(event) => {
          if (event.key === 'Enter') commitRename();
          if (event.key === 'Escape') setEditingId(null);
        }}
        className="w-full rounded-lg bg-hover px-3 py-2 text-sm outline-none"
        aria-label="Đổi tên hội thoại"
      />
    ) : (
      <ConversationRow
        conversation={conversation}
        isActive={conversation.id === activeId}
        onSelect={() => {
          onSelect(conversation.id);
          onClose();
        }}
        onRename={() => startRename(conversation)}
        onDelete={() => onDelete(conversation.id)}
        onTogglePin={() => onTogglePin(conversation.id)}
      />
    );

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 z-10 bg-black/40 md:hidden" onClick={onClose} aria-hidden="true" />
      )}

      <aside
        className={[
          'fixed inset-y-0 left-0 z-20 flex w-[260px] shrink-0 flex-col bg-sidebar',
          'transition-all duration-200 md:static md:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full',
          isCollapsed ? 'md:ml-[-260px]' : 'md:ml-0',
        ].join(' ')}
      >
        <div className="flex h-14 shrink-0 items-center justify-between px-3">
          <span className="px-1 text-[15px] font-semibold">AI Chat</span>

          <div className="flex items-center">
            <IconButton
              label={isSearching ? 'Đóng tìm kiếm' : 'Tìm hội thoại'}
              onClick={() => (isSearching ? closeSearch() : setSearching(true))}
            >
              <SearchIcon className="h-[18px] w-[18px]" />
            </IconButton>
            <IconButton label="Thu gọn thanh bên" onClick={onToggleCollapse} className="hidden md:block">
              <SidebarIcon className="h-[18px] w-[18px]" />
            </IconButton>
            <IconButton label="Đóng thanh bên" onClick={onClose} className="md:hidden">
              <CloseIcon className="h-[18px] w-[18px]" />
            </IconButton>
          </div>
        </div>

        <div className="scroll-thin flex-1 overflow-y-auto px-2 pb-2">
          <nav>
            <button
              type="button"
              onClick={() => {
                onNew();
                onClose();
              }}
              className={[ROW_CLASS, 'hover:bg-hover'].join(' ')}
            >
              <NewChatIcon className="h-[18px] w-[18px]" />
              Hội thoại mới
            </button>

            {UPCOMING_ITEMS.map(({ label, icon: Icon }) => (
              <button
                key={label}
                type="button"
                aria-disabled="true"
                title="Sắp có"
                className={[ROW_CLASS, 'hover:bg-hover'].join(' ')}
              >
                <Icon className="h-[18px] w-[18px]" />
                {label}
              </button>
            ))}
          </nav>

          {isSearching && (
            <input
              autoFocus
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => event.key === 'Escape' && closeSearch()}
              placeholder="Tìm trong hội thoại…"
              aria-label="Tìm hội thoại"
              className="mt-3 w-full rounded-lg bg-hover px-3 py-2 text-sm outline-none placeholder:text-text-faint"
            />
          )}

          <Section
            title="Đã ghim"
            count={visiblePinned.length}
            isOpen={isPinnedOpen}
            onToggle={() => setPinnedOpen((open) => !open)}
          >
            {visiblePinned.length === 0 ? (
              <p className="px-3 py-2 text-xs text-text-faint">
                Chưa ghim hội thoại nào. Rê chuột vào một hội thoại rồi bấm biểu tượng ghim.
              </p>
            ) : (
              <ul>
                {visiblePinned.map((conversation) => (
                  <li key={conversation.id}>{renderRow(conversation)}</li>
                ))}
              </ul>
            )}
          </Section>

          <Section
            title="Gần đây"
            count={visibleRecent.length}
            isOpen={isRecentsOpen}
            onToggle={() => setRecentsOpen((open) => !open)}
          >
            {visibleRecent.length === 0 ? (
              <p className="px-3 py-2 text-xs text-text-faint">
                {needle ? 'Không tìm thấy hội thoại nào.' : 'Chưa có hội thoại nào.'}
              </p>
            ) : (
              <ul>
                {visibleRecent.map((conversation) => (
                  <li key={conversation.id}>{renderRow(conversation)}</li>
                ))}
              </ul>
            )}
          </Section>
        </div>

        <div className="shrink-0 px-2 pb-2">
          <button
            type="button"
            aria-disabled="true"
            title="Sắp có"
            className={[ROW_CLASS, 'hover:bg-hover'].join(' ')}
          >
            <PricingIcon className="h-[18px] w-[18px]" />
            Xem gói và giá
          </button>

          <button
            type="button"
            onClick={onOpenSettings}
            className={[ROW_CLASS, 'hover:bg-hover'].join(' ')}
          >
            <SettingsIcon className="h-[18px] w-[18px]" />
            Cài đặt
          </button>

          <button
            type="button"
            aria-disabled="true"
            title="Sắp có"
            className={[ROW_CLASS, 'hover:bg-hover'].join(' ')}
          >
            <HelpIcon className="h-[18px] w-[18px]" />
            Trợ giúp
          </button>
        </div>

        <div className="shrink-0 border-t border-border-subtle p-4">
          {user ? (
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-hover text-sm font-medium">
                {(user.display_name || user.email).trim().charAt(0).toUpperCase()}
              </span>

              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm">{user.display_name || 'Bạn'}</span>
                <span className="block truncate text-xs text-text-faint">{user.email}</span>
              </span>

              <IconButton label="Đăng xuất" onClick={onLogout} size="sm">
                <LogoutIcon className="h-4 w-4" />
              </IconButton>
            </div>
          ) : (
            <>
              <p className="text-sm font-medium">Nhận câu trả lời hợp với bạn</p>
              <p className="mt-2 text-xs leading-relaxed text-text-muted">
                Đăng nhập để lịch sử chat được lưu lại trên máy chủ và dùng chung trên nhiều
                thiết bị. Hiện lịch sử chỉ nằm trong trình duyệt này.
              </p>

              <Button
                onClick={onLogin}
                variant="secondary"
                className="mt-3 flex w-full items-center justify-center gap-2 bg-bg"
              >
                <UserIcon className="h-4 w-4" />
                Đăng nhập
              </Button>
            </>
          )}

          <span
            title={status.hint}
            className="mt-3 flex items-center justify-center gap-2 text-xs text-text-faint"
          >
            <span className={['h-1.5 w-1.5 shrink-0 rounded-full', TONE_DOT[status.tone]].join(' ')} />
            <SparkIcon className="h-3 w-3 shrink-0" />
            <span className="truncate">{status.label}</span>
          </span>
        </div>
      </aside>
    </>
  );
}

function filterByTitle(conversations: Conversation[], needle: string): Conversation[] {
  if (!needle) return conversations;
  return conversations.filter((item) => item.title.toLowerCase().includes(needle));
}

interface SectionProps {
  title: string;
  count: number;
  isOpen: boolean;
  onToggle: () => void;
  children: ReactNode;
}

/** Collapsible sidebar group ("Đã ghim", "Gần đây"). */
function Section({ title, count, isOpen, onToggle, children }: SectionProps) {
  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex items-center gap-1 rounded-md px-3 py-1 text-xs font-medium text-text-faint transition hover:text-text-muted"
      >
        {title}
        {count > 0 && <span className="tabular-nums">({count})</span>}
        <ChevronRightIcon
          className={['h-3.5 w-3.5 transition-transform', isOpen ? 'rotate-90' : ''].join(' ')}
        />
      </button>

      {isOpen && children}
    </div>
  );
}

interface ConversationRowProps {
  conversation: Conversation;
  isActive: boolean;
  onSelect: () => void;
  onRename: () => void;
  onDelete: () => void;
  onTogglePin: () => void;
}

function ConversationRow({
  conversation,
  isActive,
  onSelect,
  onRename,
  onDelete,
  onTogglePin,
}: ConversationRowProps) {
  return (
    <div
      className={[
        'group flex items-center rounded-lg pr-1 transition',
        isActive ? 'bg-active' : 'hover:bg-hover',
      ].join(' ')}
    >
      <button
        type="button"
        onClick={onSelect}
        className="min-w-0 flex-1 truncate px-3 py-2 text-left text-sm"
        // The list omits timestamps to stay clean; the tooltip still carries them.
        title={`${conversation.title}\n${formatRelativeTime(conversation.updatedAt)}`}
      >
        {conversation.title}
      </button>

      <span className="flex shrink-0 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100">
        <IconButton
          label={conversation.isPinned ? `Bỏ ghim ${conversation.title}` : `Ghim ${conversation.title}`}
          onClick={onTogglePin}
          size="sm"
          className={conversation.isPinned ? 'text-text-primary' : ''}
        >
          <PinIcon className="h-4 w-4" />
        </IconButton>
        <IconButton label={`Đổi tên ${conversation.title}`} onClick={onRename} size="sm">
          <PencilIcon className="h-4 w-4" />
        </IconButton>
        <IconButton label={`Xóa ${conversation.title}`} tone="danger" onClick={onDelete} size="sm">
          <TrashIcon className="h-4 w-4" />
        </IconButton>
      </span>
    </div>
  );
}
