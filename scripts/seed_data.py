"""
DX-Asset - Seed Data Script (Skeleton)
Mục đích: Nạp dữ liệu khởi tạo ban đầu (Admin user, Các phòng ban mẫu, Tài sản mẫu) vào PostgreSQL.
Lưu ý: Chỉ thực thi sau khi đã chạy Alembic Migration.
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_database():
    logger.info("Bắt đầu nạp dữ liệu mẫu cho DX-Asset (Skeleton)...")
    # TODO: Khởi tạo dữ liệu người dùng Admin mặc định & các Phòng ban ban đầu
    logger.info("Hoàn tất nạp dữ liệu mẫu.")

if __name__ == "__main__":
    seed_database()
