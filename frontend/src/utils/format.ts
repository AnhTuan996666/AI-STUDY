/** Formatting helpers for display. */

import { CHAT } from '@/utils/constants';

const ELLIPSIS = '…';

export function normalizeWhitespace(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

export function truncate(text: string, maxLength: number, suffix = ELLIPSIS): string {
  if (maxLength <= 0) return '';
  return text.length <= maxLength ? text : text.slice(0, maxLength) + suffix;
}

/** Derives a conversation title from the user's first message (FR-07). */
export function deriveTitle(firstMessage: string, maxLength = CHAT.maxTitleLength): string {
  const clean = normalizeWhitespace(firstMessage);
  return clean ? truncate(clean, maxLength) : CHAT.defaultTitle;
}

/** Relative time formatting for the sidebar. */
export function formatRelativeTime(timestamp: number, now = Date.now()): string {
  const seconds = Math.max(0, Math.floor((now - timestamp) / 1000));

  if (seconds < 60) return 'vừa xong';
  if (seconds < 3_600) return `${Math.floor(seconds / 60)} phút trước`;
  if (seconds < 86_400) return `${Math.floor(seconds / 3_600)} giờ trước`;
  if (seconds < 604_800) return `${Math.floor(seconds / 86_400)} ngày trước`;

  return new Date(timestamp).toLocaleDateString('vi-VN');
}

/** Token count formatting for badges and tooltips. */
export function formatTokens(total: number | null | undefined): string {
  if (total === null || total === undefined) return '—';
  return total >= 1_000 ? `${(total / 1_000).toFixed(1)}k` : String(total);
}
