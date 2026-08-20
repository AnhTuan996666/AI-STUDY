'use client';

import { Modal } from '@/components/common/Modal';
import { useSettings } from '@/hooks/settings/useSettings';
import { SETTINGS } from '@/utils/constants';

import type { Theme } from '@/types/settings';
import type { ReactNode } from 'react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Running model name from /health, used while GET /models does not exist. */
  runningModel: string | null;
}

const THEME_OPTIONS: { value: Theme; label: string }[] = [
  { value: 'system', label: 'Theo hệ thống' },
  { value: 'light', label: 'Sáng' },
  { value: 'dark', label: 'Tối' },
];

export function SettingsModal({ isOpen, onClose, runningModel }: SettingsModalProps) {
  const { settings, models, isModelListUnavailable, error, update, setTheme } = useSettings();

  return (
    <Modal title="Cài đặt" isOpen={isOpen} onClose={onClose} size="md">
      <div className="divide-y divide-border-subtle">
        <Row label="Giao diện" hint="Áp dụng ngay, lưu lại cho lần mở sau.">
          <select
            value={settings.theme}
            onChange={(event) => setTheme(event.target.value as Theme)}
            aria-label="Chọn giao diện"
            className="rounded-lg border border-border-subtle bg-bg px-3 py-1.5 text-sm outline-none"
          >
            {THEME_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Row>

        <Row
          label="Model"
          hint={
            isModelListUnavailable
              ? 'Backend chưa có GET /models nên chỉ hiện model đang chạy.'
              : 'Model dùng cho các lượt chat tiếp theo.'
          }
        >
          <select
            value={settings.model ?? ''}
            onChange={(event) => update({ model: event.target.value || null })}
            aria-label="Chọn model"
            className="max-w-[220px] rounded-lg border border-border-subtle bg-bg px-3 py-1.5 text-sm outline-none"
          >
            <option value="">Mặc định của backend{runningModel ? ` (${runningModel})` : ''}</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name ?? model.id}
              </option>
            ))}
          </select>
        </Row>

        <Row
          label="Độ sáng tạo"
          hint={`Càng cao càng ngẫu hứng. Hiện tại: ${settings.temperature.toFixed(1)}`}
        >
          <input
            type="range"
            min={SETTINGS.minTemperature}
            max={SETTINGS.maxTemperature}
            step={SETTINGS.temperatureStep}
            value={settings.temperature}
            aria-label="Độ sáng tạo"
            onChange={(event) => update({ temperature: Number(event.target.value) })}
            className="w-40"
          />
        </Row>

        <Row label="Enter để gửi" hint="Tắt thì Enter xuống dòng, Ctrl+Enter mới gửi.">
          <Toggle
            label="Enter để gửi"
            checked={settings.send_on_enter}
            onChange={(value) => update({ send_on_enter: value })}
          />
        </Row>

        <Row label="Gợi ý câu hỏi" hint="Hiện các chip gợi ý ở màn hình chào.">
          <Toggle
            label="Gợi ý câu hỏi"
            checked={settings.show_suggestions}
            onChange={(value) => update({ show_suggestions: value })}
          />
        </Row>
      </div>

      {error && (
        <p role="alert" className="mt-4 text-xs text-danger">
          {error}
        </p>
      )}

      <p className="mt-4 text-xs leading-relaxed text-text-faint">
        Cài đặt đang lưu trong trình duyệt này. Khi backend có API <code>/settings</code>, chúng
        sẽ tự đồng bộ theo tài khoản.
      </p>
    </Modal>
  );
}

interface RowProps {
  label: string;
  hint: string;
  children: ReactNode;
}

function Row({ label, hint, children }: RowProps) {
  return (
    <div className="flex items-center justify-between gap-6 py-3.5">
      <div className="min-w-0">
        <p className="text-sm font-medium">{label}</p>
        <p className="mt-0.5 text-xs text-text-faint">{hint}</p>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

interface ToggleProps {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}

/** Toggle switch: button + aria-checked instead of a checkbox, for free-form styling. */
function Toggle({ label, checked, onChange }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={[
        'relative h-6 w-11 rounded-full transition',
        checked ? 'bg-accent' : 'bg-hover',
      ].join(' ')}
    >
      <span
        className={[
          'absolute top-1 h-4 w-4 rounded-full bg-bg transition-all',
          checked ? 'left-6' : 'left-1',
        ].join(' ')}
      />
    </button>
  );
}
