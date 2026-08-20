/** Lightweight synchronous checks for forms; validation of network data lives in `schemas/` (Zod). */

import { CHAT } from '@/utils/constants';

export function isBlank(text: string): boolean {
  return text.trim().length === 0;
}

export interface ValidationResult {
  valid: boolean;
  error?: string;
}

/** Validates message content before sending. */
export function validateMessage(text: string): ValidationResult {
  const clean = text.trim();

  if (!clean) {
    return { valid: false, error: 'Tin nhắn không được để trống.' };
  }

  if (clean.length > CHAT.maxMessageLength) {
    return {
      valid: false,
      error: `Tin nhắn quá dài (tối đa ${CHAT.maxMessageLength.toLocaleString('vi-VN')} ký tự).`,
    };
  }

  return { valid: true };
}

/** Validates the title when renaming a conversation (FR-07). */
export function validateTitle(title: string): ValidationResult {
  if (isBlank(title)) {
    return { valid: false, error: 'Tên hội thoại không được để trống.' };
  }
  return { valid: true };
}
