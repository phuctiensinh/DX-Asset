# Database Management Guide

- **Cơ chế chính**: Schema CSDL của dự án DX-Asset được quản lý tập trung 100% bằng **Alembic** (nằm trong thư mục `backend/alembic`).
- **Không khởi tạo trùng lặp**: Thư mục này không chứa file `init.sql` tạo bảng trùng lặp để tránh xung đột với Alembic Migration.
- **Seed Data**: Dữ liệu khởi tạo ban đầu được thực hiện thông qua script Python `scripts/seed_data.py`.
