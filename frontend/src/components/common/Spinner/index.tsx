/** Three bouncing dots, shown before the first token arrives. */
export function Spinner({ label = 'Đang tải' }: { label?: string }) {
  return (
    <span className="inline-flex gap-1 py-1" role="status" aria-label={label}>
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-text-muted"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
  );
}
