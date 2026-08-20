"""Utilities — hàm thuần, không phụ thuộc FastAPI hay tầng nào khác.

Quy tắc: chỉ đặt ở đây thứ dùng từ 2 nơi trở lên, hoặc thứ cần test riêng.
"""

from app.utils.text import derive_title, normalize_whitespace, truncate

__all__ = ["derive_title", "normalize_whitespace", "truncate"]
