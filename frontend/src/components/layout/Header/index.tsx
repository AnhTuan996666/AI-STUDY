'use client';

import { ModelPicker } from '@/components/chat/ModelPicker';
import { Button } from '@/components/common/Button';
import { NewChatIcon, SidebarIcon } from '@/components/common/Icon';
import { IconButton } from '@/components/common/IconButton';

import type { HealthState } from '@/types/chat';
import type { User } from '@/types/auth';

interface HeaderProps {
  health: HealthState;
  user: User | null;
  /** The sidebar is collapsed out of the layout on large screens. */
  isSidebarCollapsed: boolean;
  onOpenSidebar: () => void;
  onExpandSidebar: () => void;
  onNew: () => void;
  onLogin: () => void;
  onRegister: () => void;
}

/** Top bar: sidebar toggle, model picker, account. Deliberately borderless, no conversation title. */
export function Header({
  health,
  user,
  isSidebarCollapsed,
  onOpenSidebar,
  onExpandSidebar,
  onNew,
  onLogin,
  onRegister,
}: HeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-0.5 px-3">
      <IconButton label="Mở thanh bên" onClick={onOpenSidebar} className="md:hidden">
        <SidebarIcon className="h-[18px] w-[18px]" />
      </IconButton>

      {isSidebarCollapsed && (
        <>
          <IconButton label="Mở thanh bên" onClick={onExpandSidebar} className="hidden md:block">
            <SidebarIcon className="h-[18px] w-[18px]" />
          </IconButton>
          <IconButton label="Hội thoại mới" onClick={onNew} className="hidden md:block">
            <NewChatIcon className="h-[18px] w-[18px]" />
          </IconButton>
        </>
      )}

      <ModelPicker health={health} />

      <div className="ml-auto flex items-center gap-2">
        <IconButton label="Hội thoại mới" onClick={onNew} className="md:hidden">
          <NewChatIcon className="h-[18px] w-[18px]" />
        </IconButton>

        {user ? (
          <span
            title={user.email}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-hover text-sm font-medium"
            aria-label={`Đang đăng nhập: ${user.display_name}`}
          >
            {initialOf(user.display_name || user.email)}
          </span>
        ) : (
          <>
            <Button size="sm" onClick={onLogin} className="px-4 py-2">
              Đăng nhập
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={onRegister}
              className="hidden px-4 py-2 sm:block"
            >
              Đăng ký miễn phí
            </Button>
          </>
        )}
      </div>
    </header>
  );
}

function initialOf(name: string): string {
  return name.trim().charAt(0).toUpperCase() || '?';
}
