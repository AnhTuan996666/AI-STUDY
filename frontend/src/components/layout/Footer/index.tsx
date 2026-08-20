/** Disclaimer on the welcome screen only; once chatting, the composer carries its own hint. */
export function Footer() {
  return (
    <footer className="shrink-0 px-4 pb-3 text-center text-xs leading-relaxed text-text-faint">
      <p>
        AI Chat chạy model mã nguồn mở tự host — nội dung có thể chưa chính xác, hãy kiểm chứng
        lại.
      </p>
      <p>Lịch sử hội thoại đang lưu trong trình duyệt này, chưa gửi lên máy chủ nào.</p>
    </footer>
  );
}
