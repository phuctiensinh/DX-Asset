# DX-Asset: Open-Source Digital Asset Lifecycle Management Platform

> **Phần mềm Nguồn mở OLP 2026** — Chủ đề: Xây dựng Hệ điều hành Doanh nghiệp số (DX-OS / DX-Lab)  
> **Giấy phép**: MIT License (OSI-Approved)  
> **Đơn vị phát triển**: Trường Đại học Thủ Dầu Một (TDMU)  

---

## 📌 Giới thiệu Dự án

**DX-Asset** là nền tảng web mã nguồn mở quản lý tập trung toàn bộ vòng đời tài sản số và thiết bị nội bộ doanh nghiệp (laptops, màn hình, máy in, router...). Sản phẩm hỗ trợ chuyển đổi các quy trình quản lý thủ công rời rạc (Excel, giấy tờ, tin nhắn) thành một quy trình số hóa chuẩn hóa, minh bạch, có khả năng truy vết lịch sử sở hữu & bảo trì hoàn chỉnh, tích hợp Trợ lý AI hỗ trợ ra quyết định theo đúng khung kiến trúc **DX-OS**.

---

## 🎯 Bài toán Thực tế & Giải pháp

### Vấn đề Vận hành
- Quản lý thiết bị rời rạc trên file Excel, thiếu đồng bộ giữa các phòng ban.
- Mất truy vết lịch sử khi thiết bị luân chuyển hoặc qua nhiều lần sửa chữa.
- Quy trình báo hỏng sự cố chậm trễ, thiếu minh bạch tiến độ.
- Thiếu báo cáo thống kê định lượng theo thời gian thực cho cấp quản lý.

### Giải pháp của DX-Asset
- **Hồ sơ số tài sản (QR Asset Passport)**: Mỗi thiết bị có 01 mã QR định danh duy nhất chứa `asset_code`.
- **Luồng nghiệp vụ khép kín**: Bàn giao $\rightarrow$ Báo hỏng $\rightarrow$ Sửa chữa $\rightarrow$ Thu hồi.
- **Bảo toàn 100% Lịch sử**: Toàn bộ biến động được ghi nhật ký Timeline không ghi đè.
- **Trợ lý AI Tùy chọn (Human-in-the-loop)**: Gợi ý phân loại sự cố và độ ưu tiên từ mô tả lỗi (hỗ trợ Rule-based Fallback khi không có mạng/API Key).

---

## 🏛️ Ánh xạ Kiến trúc 4 Không gian DX-OS (H-P-D-I)

- **[H] Human (Nhân sự)**: Quản trị định danh tập trung (4 vai trò: `ADMIN`, `IT_ASSET_MANAGER`, `EMPLOYEE`, `MANAGER`), quản lý người dùng và phòng ban.
- **[P] Process (Quy trình)**: Luồng Cấp phát $\rightarrow$ Thu hồi $\rightarrow$ Báo hỏng $\rightarrow$ Bảo trì khép kín, thiết lập ràng buộc trạng thái thiết bị hợp lệ (Poka-yoke).
- **[D] Data (Dữ liệu)**: Lưu trữ tập trung PostgreSQL (Single Source of Truth), bảo lưu lịch sử Timeline, hiển thị Dashboard thời gian thực.
- **[I] Intelligence (AI)**: Trợ lý AI phân tích mô tả lỗi gợi ý tag `Category` và `Priority` hỗ trợ con người ra quyết định.

---

## 🛠️ Công nghệ Sử dụng

- **Frontend**: Next.js 14 (App Router), TypeScript 5, Tailwind CSS, shadcn/ui.
- **Backend**: Python 3.12, FastAPI 0.111, Pydantic v2, SQLAlchemy 2.0, Alembic (Migration).
- **Database**: PostgreSQL 16.
- **Containerization**: Docker & Docker Compose v2.

---

## 🚀 Hướng dẫn Cài đặt & Chạy ứng dụng từ Mã nguồn

### Yêu cầu Tiền đề
- Docker & Docker Compose (v2.x)
- Git (v2.x)

### Các bước Chạy ứng dụng bằng Docker Compose (1 lệnh)

1. **Clone mã nguồn**:
   ```bash
   git clone https://github.com/ten-nhom/dx-asset.git
   cd dx-asset
   ```

2. **Cấu hình biến môi trường**:
   ```bash
   cp .env.example .env
   ```

3. **Khởi chạy toàn bộ hệ thống bằng Docker Compose**:
   ```bash
   docker compose up -d
   ```

4. **Truy cập ứng dụng**:
   - **Frontend App**: `http://localhost:3000`
   - **Backend REST API Specs**: `http://localhost:8000/docs`

---

## 📜 Giấy phép Mã nguồn mở

Dự án được phân phối dưới giấy phép [MIT License](LICENSE).
