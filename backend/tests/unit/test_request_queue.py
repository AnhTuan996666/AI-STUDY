"""Test hàng đợi cục bộ: trần song song, FIFO, vị trí, đầy và quá hạn."""

from __future__ import annotations

import asyncio

import pytest

from app.core.exceptions import QueueFullError, QueueTimeoutError
from app.modules.llm.queue.local import LocalRequestQueue


def make_queue(
    max_concurrent: int = 2,
    max_queue: int = 3,
    wait_timeout_seconds: float = 5.0,
) -> LocalRequestQueue:
    return LocalRequestQueue(
        max_concurrent=max_concurrent,
        max_queue=max_queue,
        wait_timeout_seconds=wait_timeout_seconds,
    )


async def drain(ticket) -> None:  # noqa: ANN001 - QueueTicket, tránh import thừa
    """Chờ tới lượt, bỏ qua các mốc vị trí."""
    async for _ in ticket.wait_for_turn():
        pass


@pytest.mark.asyncio
async def test_admits_up_to_max_concurrent_immediately() -> None:
    queue = make_queue(max_concurrent=2)

    first = await queue.enqueue("a")
    second = await queue.enqueue("b")

    assert first.is_admitted
    assert second.is_admitted
    assert queue.stats().running == 2
    assert queue.stats().waiting == 0


@pytest.mark.asyncio
async def test_extra_request_waits_with_a_position() -> None:
    queue = make_queue(max_concurrent=1)

    running = await queue.enqueue("a")
    waiting = await queue.enqueue("b")

    assert running.is_admitted
    assert not waiting.is_admitted
    assert waiting.position == 1
    assert queue.stats().waiting == 1


@pytest.mark.asyncio
async def test_release_admits_the_next_in_line() -> None:
    queue = make_queue(max_concurrent=1)

    running = await queue.enqueue("a")
    waiting = await queue.enqueue("b")
    turn = asyncio.create_task(drain(waiting))

    await asyncio.sleep(0)  # cho task kịp vào trạng thái chờ
    await running.release()
    await asyncio.wait_for(turn, timeout=1)

    assert waiting.is_admitted
    assert queue.stats().running == 1
    assert queue.stats().waiting == 0


@pytest.mark.asyncio
async def test_serves_in_fifo_order() -> None:
    queue = make_queue(max_concurrent=1)

    running = await queue.enqueue("a")
    second = await queue.enqueue("b")
    third = await queue.enqueue("c")

    assert second.position == 1
    assert third.position == 2

    await running.release()

    assert second.is_admitted
    assert not third.is_admitted
    assert third.position == 1  # nhích lên sau khi người trước được phục vụ


@pytest.mark.asyncio
async def test_reports_position_updates_while_waiting() -> None:
    queue = make_queue(max_concurrent=1)

    running = await queue.enqueue("a")
    middle = await queue.enqueue("b")
    last = await queue.enqueue("c")

    seen: list[int] = []

    async def watch() -> None:
        async for position in last.wait_for_turn():
            seen.append(position)

    task = asyncio.create_task(watch())
    await asyncio.sleep(0)

    await running.release()  # last: 2 -> 1
    await asyncio.sleep(0)
    await middle.release()  # last: được nhận
    await asyncio.wait_for(task, timeout=1)

    assert seen == [2, 1]
    assert last.is_admitted


@pytest.mark.asyncio
async def test_rejects_when_queue_is_full() -> None:
    queue = make_queue(max_concurrent=1, max_queue=1)

    await queue.enqueue("a")  # đang chạy
    await queue.enqueue("b")  # chỗ chờ duy nhất

    with pytest.raises(QueueFullError):
        await queue.enqueue("c")


@pytest.mark.asyncio
async def test_gives_up_after_wait_timeout() -> None:
    queue = make_queue(max_concurrent=1, wait_timeout_seconds=0.05)

    await queue.enqueue("a")
    waiting = await queue.enqueue("b")

    with pytest.raises(QueueTimeoutError):
        await drain(waiting)

    # Vé quá hạn phải rời khỏi hàng đợi, không chiếm chỗ của người khác.
    assert queue.stats().waiting == 0


@pytest.mark.asyncio
async def test_releasing_a_waiting_ticket_frees_its_slot_in_line() -> None:
    """Client ngắt kết nối lúc đang xếp hàng -> phải biến mất khỏi hàng đợi."""
    queue = make_queue(max_concurrent=1)

    await queue.enqueue("a")
    abandoned = await queue.enqueue("b")
    last = await queue.enqueue("c")

    await abandoned.release()

    assert queue.stats().waiting == 1
    assert last.position == 1


@pytest.mark.asyncio
async def test_release_is_idempotent() -> None:
    queue = make_queue(max_concurrent=2)

    ticket = await queue.enqueue("a")
    await ticket.release()
    await ticket.release()

    assert queue.stats().running == 0


@pytest.mark.asyncio
async def test_slot_context_manager_releases_on_error() -> None:
    queue = make_queue(max_concurrent=1)

    with pytest.raises(RuntimeError):
        async with queue.slot("a"):
            raise RuntimeError("lỗi giữa chừng")

    assert queue.stats().running == 0


@pytest.mark.asyncio
async def test_eta_uses_measured_duration() -> None:
    queue = make_queue(max_concurrent=1)

    ticket = await queue.enqueue("a")
    await asyncio.sleep(0.05)
    await ticket.release()

    stats = queue.stats()
    assert stats.average_duration_ms is not None
    assert stats.eta_seconds(0) is None  # đang được phục vụ thì không còn phải chờ
    assert stats.eta_seconds(4) is not None
