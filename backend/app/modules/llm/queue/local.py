"""Hàng đợi chạy trong 1 process bằng asyncio.

Giới hạn: chỉ đúng khi backend chạy **một** worker. Nhiều worker/instance thì mỗi
tiến trình có hàng đợi riêng, tổng số lượt xuống GPU sẽ là `workers × max_concurrent`
— lúc đó phải đổi sang bản Redis (xem `factory.py`).

Vì sao không dùng thẳng `asyncio.Semaphore`: semaphore không cho biết mình đang
đứng thứ mấy, không giới hạn được số người chờ, và không đảm bảo FIFO. Ba thứ đó
đều cần cho trải nghiệm "xếp hàng có thông báo" thay vì "đứng im rồi timeout".
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import AsyncIterator

from app.core.exceptions import QueueFullError, QueueTimeoutError
from app.core.logging import get_logger
from app.modules.llm.queue.base import QueueStats, QueueTicket, RequestQueue

logger = get_logger(__name__)

# Trọng số EWMA cho thời lượng trung bình một lượt: càng nhỏ càng mượt, càng chậm
# phản ứng khi tải đổi. 0.2 ≈ nhớ khoảng 5 lượt gần nhất.
_EWMA_ALPHA = 0.2


class _LocalTicket(QueueTicket):
    """Vé của `LocalRequestQueue`. Chỉ `LocalRequestQueue` được tạo/điều khiển."""

    def __init__(self, queue: LocalRequestQueue, key: str, wait_timeout: float) -> None:
        self._queue = queue
        self._key = key
        self._wait_timeout = wait_timeout
        self._enqueued_at = time.monotonic()
        self._admitted_at: float | None = None
        self._released = False

        # `_admitted`: đã tới lượt. `_changed`: hàng đợi vừa xê dịch -> đọc lại vị trí.
        self._admitted = asyncio.Event()
        self._changed = asyncio.Event()

    # --- hợp đồng QueueTicket -------------------------------------------

    @property
    def key(self) -> str:
        return self._key

    @property
    def is_admitted(self) -> bool:
        return self._admitted.is_set()

    @property
    def position(self) -> int:
        return 0 if self._admitted.is_set() else self._queue.position_of(self)

    @property
    def waited_ms(self) -> int:
        end = self._admitted_at if self._admitted_at is not None else time.monotonic()
        return int((end - self._enqueued_at) * 1000)

    async def wait_for_turn(self) -> AsyncIterator[int]:
        deadline = self._enqueued_at + self._wait_timeout
        reported = -1

        while not self._admitted.is_set():
            current = self.position
            if current > 0 and current != reported:
                reported = current
                yield current

            self._changed.clear()
            # Có thể vừa được nhận ngay giữa hai lệnh trên -> kiểm tra lại trước khi chờ.
            if self._admitted.is_set():
                break

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._queue.discard(self)
                raise QueueTimeoutError(
                    f"Hệ thống đang quá tải, bạn đã chờ quá {int(self._wait_timeout)} giây. "
                    "Vui lòng thử lại sau."
                )

            try:
                await asyncio.wait_for(self._changed.wait(), timeout=remaining)
            except TimeoutError:
                self._queue.discard(self)
                raise QueueTimeoutError(
                    f"Hệ thống đang quá tải, bạn đã chờ quá {int(self._wait_timeout)} giây. "
                    "Vui lòng thử lại sau."
                ) from None

    async def release(self) -> None:
        if self._released:
            return

        self._released = True
        self._queue.release_ticket(self)

    # --- chỉ dành cho LocalRequestQueue ----------------------------------

    def admit(self) -> None:
        self._admitted_at = time.monotonic()
        self._admitted.set()
        self._changed.set()

    def wake(self) -> None:
        self._changed.set()

    @property
    def duration_ms(self) -> int | None:
        """Thời lượng thực sự chiếm slot; None nếu chưa từng được nhận."""
        if self._admitted_at is None:
            return None
        return int((time.monotonic() - self._admitted_at) * 1000)


class LocalRequestQueue(RequestQueue):
    """FIFO có trần số lượt song song và trần số người chờ.

    Không cần khóa: mọi thao tác đổi trạng thái đều chạy trọn vẹn trong một bước
    của event loop (không có `await` xen giữa lúc đọc và lúc ghi).
    """

    name = "local"

    def __init__(
        self,
        max_concurrent: int,
        max_queue: int,
        wait_timeout_seconds: float,
    ) -> None:
        self._max_concurrent = max(1, max_concurrent)
        self._max_queue = max(0, max_queue)
        self._wait_timeout = wait_timeout_seconds
        self._running = 0
        self._waiting: deque[_LocalTicket] = deque()
        self._average_duration_ms: float | None = None

    # --- hợp đồng RequestQueue -------------------------------------------

    async def enqueue(self, key: str) -> QueueTicket:
        ticket = _LocalTicket(self, key, self._wait_timeout)

        # Chỉ được đi thẳng khi còn slot VÀ không có ai đang chờ — nếu không sẽ
        # chen ngang người đã xếp hàng trước.
        if self._running < self._max_concurrent and not self._waiting:
            self._running += 1
            ticket.admit()
            return ticket

        if len(self._waiting) >= self._max_queue:
            logger.warning(
                "queue.full key=%s running=%d waiting=%d",
                key,
                self._running,
                len(self._waiting),
            )
            raise QueueFullError(
                "Hệ thống đang phục vụ tối đa số người dùng. Vui lòng thử lại sau ít phút."
            )

        self._waiting.append(ticket)
        logger.info(
            "queue.wait key=%s position=%d running=%d",
            key,
            len(self._waiting),
            self._running,
        )
        return ticket

    def stats(self) -> QueueStats:
        return QueueStats(
            running=self._running,
            waiting=len(self._waiting),
            max_concurrent=self._max_concurrent,
            max_queue=self._max_queue,
            average_duration_ms=(
                None if self._average_duration_ms is None else int(self._average_duration_ms)
            ),
        )

    # --- nội bộ, do _LocalTicket gọi ngược lại ---------------------------

    def position_of(self, ticket: _LocalTicket) -> int:
        try:
            return self._waiting.index(ticket) + 1
        except ValueError:
            return 0

    def discard(self, ticket: _LocalTicket) -> None:
        """Bỏ một vé đang chờ (client ngắt kết nối hoặc chờ quá hạn)."""
        try:
            self._waiting.remove(ticket)
        except ValueError:
            return

        self._notify()

    def release_ticket(self, ticket: _LocalTicket) -> None:
        if not ticket.is_admitted:
            self.discard(ticket)
            return

        self._record_duration(ticket)
        self._running = max(0, self._running - 1)
        self._pump()

    # --- helper ----------------------------------------------------------

    def _pump(self) -> None:
        """Lấp đầy slot trống bằng những người chờ lâu nhất."""
        while self._waiting and self._running < self._max_concurrent:
            nxt = self._waiting.popleft()
            self._running += 1
            nxt.admit()

        self._notify()

    def _notify(self) -> None:
        """Báo cho mọi người còn chờ đọc lại vị trí của mình."""
        for ticket in self._waiting:
            ticket.wake()

    def _record_duration(self, ticket: _LocalTicket) -> None:
        duration = ticket.duration_ms
        if duration is None:
            return

        if self._average_duration_ms is None:
            self._average_duration_ms = float(duration)
        else:
            self._average_duration_ms = (
                _EWMA_ALPHA * duration + (1 - _EWMA_ALPHA) * self._average_duration_ms
            )
