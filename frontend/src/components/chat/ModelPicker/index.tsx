'use client';

import { useEffect, useRef, useState } from 'react';

import { CheckIcon, ChevronDownIcon } from '@/components/common/Icon';
import { useSettings } from '@/hooks/settings/useSettings';
import { describeHealth } from '@/utils/health';

import type { HealthState } from '@/types/chat';

interface ModelPickerProps {
  health: HealthState;
}

const TONE_DOT: Record<'online' | 'muted' | 'danger', string> = {
  online: 'bg-online',
  muted: 'bg-text-faint',
  danger: 'bg-danger',
};

/** Model switcher; without `GET /models` the list is empty, so it shows the running model and stays closed. */
export function ModelPicker({ health }: ModelPickerProps) {
  const { settings, models, setModel } = useSettings();
  const [isOpen, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const status = describeHealth(health);
  const runningModel = health.kind === 'ok' ? health.health.model : null;
  const hasChoices = models.length > 0;

  const selected = models.find((model) => model.id === settings.model);
  const label = selected?.name ?? selected?.id ?? runningModel ?? status.label;

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
    <div ref={containerRef} className="relative ml-1">
      <button
        type="button"
        aria-haspopup={hasChoices ? 'menu' : undefined}
        aria-expanded={hasChoices ? isOpen : undefined}
        aria-disabled={hasChoices ? undefined : 'true'}
        title={hasChoices ? status.hint : `${status.hint} · Backend chưa có API danh sách model`}
        onClick={() => hasChoices && setOpen((open) => !open)}
        className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-[15px] font-medium transition hover:bg-hover"
      >
        <span className={['h-1.5 w-1.5 shrink-0 rounded-full', TONE_DOT[status.tone]].join(' ')} />
        <span className="max-w-[40vw] truncate">{label}</span>
        <ChevronDownIcon className="h-4 w-4 shrink-0 text-text-faint" />
      </button>

      {isOpen && hasChoices && (
        <div
          role="menu"
          className="absolute top-full left-0 z-30 mt-1 w-[300px] rounded-2xl border border-border-subtle bg-composer p-1.5 shadow-[var(--shadow-popover)]"
        >
          <MenuRow
            label={`Mặc định của backend${runningModel ? ` (${runningModel})` : ''}`}
            isSelected={settings.model === null}
            onSelect={() => {
              setModel(null);
              setOpen(false);
            }}
          />

          {models.map((model) => (
            <MenuRow
              key={model.id}
              label={model.name ?? model.id}
              description={model.description ?? undefined}
              isSelected={settings.model === model.id}
              onSelect={() => {
                setModel(model.id);
                setOpen(false);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface MenuRowProps {
  label: string;
  description?: string;
  isSelected: boolean;
  onSelect: () => void;
}

function MenuRow({ label, description, isSelected, onSelect }: MenuRowProps) {
  return (
    <button
      type="button"
      role="menuitemradio"
      aria-checked={isSelected}
      onClick={onSelect}
      className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition hover:bg-hover"
    >
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm">{label}</span>
        {description && (
          <span className="block truncate text-xs text-text-faint">{description}</span>
        )}
      </span>

      {isSelected && <CheckIcon className="h-4 w-4 shrink-0" />}
    </button>
  );
}
