import { Spinner } from '@/components/common/Spinner';

import type { QueuePlace } from '@/types/chat';

interface QueueNoticeProps {
  queue: QueuePlace;
}

/** Queue indicator — without it, users waiting behind others just see a frozen screen. */
export function QueueNotice({ queue }: QueueNoticeProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-3 rounded-xl border border-border-subtle bg-bubble px-4 py-3 text-sm text-text-muted"
    >
      <Spinner label="Đang xếp hàng" />
      <span>
        Hệ thống đang bận — bạn đứng thứ{' '}
        <strong className="text-text-primary">{queue.position}</strong>
        {queue.queueSize !== null && queue.queueSize > 1 && <> trong {queue.queueSize} người chờ</>}.
        {queue.etaSeconds !== null && <> Ước tính khoảng {formatEta(queue.etaSeconds)} nữa.</>}
      </span>
    </div>
  );
}

/** Seconds to a short human string ("45 giây", "2 phút"). */
function formatEta(seconds: number): string {
  if (seconds < 60) return `${seconds} giây`;
  return `${Math.round(seconds / 60)} phút`;
}
