"""Hợp đồng của lớp hàng đợi đặt trước model server.

Vì sao cần: GPU chỉ sinh được N lượt cùng lúc. Nếu không chặn ở đây thì request
thứ N+1 vẫn đi thẳng xuống Ollama và nằm trong hàng đợi *của Ollama* cho tới khi
timeout — người dùng thấy màn hình đứng im mà không biết vì sao, còn server thì
không có cách nào báo "đang bận" hay "bạn đứng thứ mấy".

Tầng này chỉ định nghĩa **hợp đồng**, không định nghĩa cách chạy:

- `LocalRequestQueue` — 1 process, dùng asyncio. Đủ cho giai đoạn 1.
- (sau này) `RedisRequestQueue` — nhiều instance dùng chung 1 GPU pool.

Đổi bản chạy chỉ cần sửa `app/services/queue/factory.py` + biến `QUEUE_BACKEND`.
API, ChatService và frontend không phải sửa dòng nào (NFR-04).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class QueueStats:
    """Ảnh chụp trạng thái hàng đợi tại một thời điểm (dùng cho /health & log)."""

    running: int
    """Số lượt đang thực sự chạy trên model server."""

    waiting: int
    """Số lượt đang xếp hàng."""

    max_concurrent: int
    """Trần số lượt chạy song song."""

    max_queue: int
    """Sức chứa hàng đợi; vượt quá thì từ chối ngay bằng QueueFullError."""

    average_duration_ms: int | None = None
    """Thời lượng trung bình một lượt (EWMA). None khi chưa có mẫu nào."""

    @property
    def is_saturated(self) -> bool:
        """True khi mọi slot đã bận — dùng để cảnh báo sớm trước khi hàng đợi đầy."""
        return self.running >= self.max_concurrent

    def eta_seconds(self, position: int) -> int | None:
        """Ước lượng thời gian chờ cho người đứng thứ `position`.

        Chỉ là ước lượng thô để hiển thị cho người dùng, không phải cam kết.
        """
        if self.average_duration_ms is None or position <= 0:
            return None

        rounds = -(-position // max(1, self.max_concurrent))  # chia lên
        return max(1, round(rounds * self.average_duration_ms / 1000))


class QueueTicket(ABC):
    """Chỗ đã giữ trong hàng đợi.

    Vòng đời: `enqueue()` -> `wait_for_turn()` (chờ tới lượt) -> chạy -> `release()`.
    Bắt buộc `release()` trong `finally`, kể cả khi client ngắt kết nối giữa chừng,
    nếu không slot sẽ rò rỉ và hàng đợi tắc vĩnh viễn.
    """

    @property
    @abstractmethod
    def key(self) -> str:
        """Khóa định danh người gọi (user id hoặc IP) — dành cho log & xếp hàng công bằng."""

    @property
    @abstractmethod
    def is_admitted(self) -> bool:
        """True khi đã tới lượt và đang giữ một slot."""

    @property
    @abstractmethod
    def position(self) -> int:
        """Vị trí hiện tại: 0 = đang được phục vụ, 1 = người kế tiếp."""

    @property
    @abstractmethod
    def waited_ms(self) -> int:
        """Thời gian đã nằm chờ trong hàng đợi."""

    @abstractmethod
    def wait_for_turn(self) -> AsyncIterator[int]:
        """Chờ tới lượt, yield vị trí mỗi khi nó thay đổi (chỉ yield vị trí > 0).

        Kết thúc bình thường = đã được cấp slot. Raise `QueueTimeoutError` nếu chờ
        quá `wait_timeout_seconds`.
        """

    @abstractmethod
    async def release(self) -> None:
        """Trả slot lại cho hàng đợi. Gọi nhiều lần vẫn an toàn."""


class RequestQueue(ABC):
    """Hợp đồng mà mọi bản hàng đợi phải thỏa mãn."""

    name: str

    @abstractmethod
    async def enqueue(self, key: str) -> QueueTicket:
        """Giữ chỗ, trả về ngay (không chờ). Raise `QueueFullError` khi hàng đợi đầy."""

    @abstractmethod
    def stats(self) -> QueueStats:
        """Trạng thái hiện tại của hàng đợi."""

    async def aclose(self) -> None:  # noqa: B027
        """Giải phóng tài nguyên (mặc định: không có gì)."""

    @asynccontextmanager
    async def slot(self, key: str) -> AsyncIterator[QueueTicket]:
        """Bản rút gọn cho luồng không cần báo vị trí (POST /chat non-streaming).

        Chờ tới lượt rồi mới vào thân `async with`, và luôn trả slot khi thoát.
        """
        ticket = await self.enqueue(key)
        try:
            async for _position in ticket.wait_for_turn():
                pass  # non-streaming thì không có kênh nào để báo vị trí -> chỉ chờ
            yield ticket
        finally:
            await ticket.release()
