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

## 🤖 Tính năng AI (Ollama, chạy cục bộ)

AI chạy bằng model `qwen2.5:3b` trên chính máy chủ (Ollama), không gửi dữ liệu ra ngoài. AI **chỉ gợi ý**, không tự lưu hay thay đổi dữ liệu.

| Tính năng | Ở đâu | Ai dùng được |
|---|---|---|
| Gợi ý phân loại & mức ưu tiên khi báo hỏng | Form "Báo cáo sự cố" → nút **Gợi ý bằng AI** → **Áp dụng gợi ý** | Mọi người dùng |
| Tóm tắt sự cố | Chi tiết sự cố → **Trợ lý AI** → **Tóm tắt sự cố** | Người xem được phiếu (nhân viên chỉ với phiếu của mình) |
| Gợi ý các bước xử lý (dựa trên sự cố tương tự đã giải quyết) | Chi tiết sự cố → **Gợi ý các bước xử lý** | ADMIN, IT_ASSET_MANAGER |
| Phân loại queue xử lý | API `POST /incidents/{id}/classify` | ADMIN, IT_ASSET_MANAGER |
| Trợ lý hỏi đáp dữ liệu | Trang **Trợ lý AI** | Theo vai trò |

- Khi Ollama tắt, quá chậm hoặc trả kết quả sai định dạng, hệ thống tự dùng **phương án dự phòng theo quy tắc**. Giao diện ghi rõ kết quả đến từ **AI (Ollama)** hay **Dự phòng theo quy tắc**.
- Lần gọi đầu tiên sau khi khởi động cần nạp model (khoảng 10–15 giây với GPU, lâu hơn với CPU). Các lần sau với GPU chỉ khoảng 1–3 giây.
- Cấu hình trong `.env`: `OLLAMA_ENABLED`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`.

---

## 🛠️ Công nghệ Sử dụng

- **Frontend**: Next.js 14 (App Router), TypeScript 5, Tailwind CSS, shadcn/ui.
- **Backend**: Python 3.12, FastAPI 0.111, Pydantic v2, SQLAlchemy 2.0, Alembic (Migration).
- **Database**: PostgreSQL 16.
- **Containerization**: Docker & Docker Compose v2.

---

## 🚀 Hướng dẫn Cài đặt & Chạy ứng dụng

Có 2 cách chạy. **Cách A (Docker)** là cách khuyến nghị cho người mới clone về: chỉ cần cài Docker, không cần cài Python hay Node.js.

### Yêu cầu

| Thành phần | Cách A (Docker) | Cách B (Dev local) |
|---|---|---|
| Git | ✅ | ✅ |
| Docker Desktop (Compose v2) | ✅ | ✅ (chạy PostgreSQL, Keycloak, SeaweedFS, Ollama) |
| Python 3.12 | – | ✅ |
| Node.js 20 | – | ✅ |

Tài nguyên máy: RAM trống tối thiểu ~6 GB, ổ đĩa trống ~8 GB (model AI `qwen2.5:3b` nặng ~1.9 GB).

---

### Cách A — Chạy toàn bộ bằng Docker (khuyến nghị)

1. **Clone mã nguồn**
   ```bash
   git clone https://github.com/phuctiensinh/DX-Asset.git
   cd DX-Asset
   ```

2. **Tạo file biến môi trường** (Windows PowerShell dùng `copy` thay cho `cp`)
   ```bash
   cp .env.example .env
   ```
   Có thể giữ nguyên giá trị mặc định khi chạy thử trên máy cá nhân. Khi triển khai thật, **bắt buộc** đổi `SECRET_KEY`, `POSTGRES_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`.

3. **Build và khởi động**
   ```bash
   docker compose up -d --build
   ```
   Lần đầu mất khoảng 5–10 phút (tải image, build frontend/backend, tải model AI). Backend tự động chạy migration và nạp dữ liệu mẫu khi khởi động.

4. **Kiểm tra trạng thái**
   ```bash
   docker compose ps -a
   ```
   Các service phải ở trạng thái `Up` / `healthy`. Riêng `dx_asset_ollama_pull` là job tải model AI một lần, chạy xong sẽ `Exited (0)`, đó là bình thường.

5. **Truy cập**

   | Dịch vụ | Địa chỉ |
   |---|---|
   | Ứng dụng web | http://localhost:3000 |
   | API docs (Swagger) | http://localhost:8000/docs |
   | Keycloak Admin Console | http://localhost:8080 (tài khoản lấy từ `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD` trong `.env`) |

> ⚠️ Luôn truy cập bằng `localhost`, **không** dùng `127.0.0.1` hay IP máy. Token đăng nhập gắn với địa chỉ `localhost`; dùng địa chỉ khác sẽ bị lỗi 401.

#### Dùng GPU NVIDIA cho AI (tùy chọn)

Mặc định Ollama chạy bằng CPU để chạy được trên mọi máy. Nếu máy có card NVIDIA:
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

---

### Cách B — Chạy dev local (dành cho người phát triển)

Backend và frontend chạy trực tiếp trên máy (có hot-reload); các dịch vụ hạ tầng chạy bằng Docker.

1. Tạo file môi trường:
   ```bash
   cp .env.example .env
   cp frontend/.env.local.example frontend/.env.local
   ```
2. Cài thư viện backend (tạo virtualenv trong `backend/.venv`):
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   cd ..
   ```
3. Cài thư viện frontend:
   ```bash
   cd frontend
   npm install
   cd ..
   ```
4. Trên Windows, chạy `start-dev.bat`. Script sẽ khởi động hạ tầng Docker, chạy migration, mở backend (cổng 8000) và frontend (cổng 3000). Script tự dùng GPU nếu phát hiện `nvidia-smi`, và tự dừng container `backend`/`frontend` của Cách A để tránh trùng cổng.
5. Nạp dữ liệu mẫu (chỉ cần lần đầu):
   ```bash
   cd backend
   .venv\Scripts\python -m scripts.seed_data
   ```
6. Tải model AI (chỉ cần lần đầu):
   ```bash
   docker exec dx_asset_ollama ollama pull qwen2.5:3b
   ```

---

### Tài khoản đăng nhập

Hệ thống dùng **Keycloak SSO**. Mỗi máy có một Keycloak riêng, được tạo mới từ `docker/keycloak/realm-export.json`, nên **tài khoản không được chia sẻ giữa các máy**.

- **Người dùng mới**: tại trang đăng nhập, bấm **"Đăng ký Tài khoản Mới"**. Nếu Keycloak hiện trang đăng nhập, bấm link **Register** ở cuối khung, điền thông tin rồi bấm **Register**. Sau khi đăng ký, hệ thống tự đăng nhập và tạo tài khoản với vai trò `EMPLOYEE`.
- **Quản trị viên (ADMIN)**: hệ thống chỉ cho phép **một** tài khoản ADMIN duy nhất (System Owner), gắn với email `2424801030008@student.tdmu.edu.vn`. Đăng ký Keycloak bằng đúng email này sẽ được liên kết với tài khoản ADMIN có sẵn trong dữ liệu mẫu.
- ADMIN có thể đổi vai trò người dùng khác (`IT_ASSET_MANAGER`, `MANAGER`, `EMPLOYEE`) tại trang **Người dùng**.

---

### Lệnh Docker thường dùng

| Mục đích | Lệnh |
|---|---|
| Xem log backend | `docker compose logs -f backend` |
| Dừng hệ thống (giữ dữ liệu) | `docker compose stop` |
| Khởi động lại | `docker compose up -d` |
| Build lại sau khi `git pull` / sửa code | `docker compose up -d --build` |
| Xóa container (giữ dữ liệu) | `docker compose down` |
| ⚠️ Xóa **toàn bộ dữ liệu** (DB, tài khoản Keycloak, file đính kèm, model AI) | `docker compose down -v` |

---

### Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân & cách xử lý |
|---|---|
| Đăng nhập/đăng ký xong bị quay về trang Login, console báo `401` ở `/auth/me` | Truy cập bằng `localhost:3000` (không dùng `127.0.0.1`). Xóa Local Storage của trang (F12 → Application → Local Storage) rồi thử lại. Xem lý do cụ thể bằng `docker compose logs backend`. Nếu Keycloak vừa khởi động, đợi ~1 phút. |
| `port is already allocated` (5432, 8080, 3000, 8000…) | Có chương trình khác đang dùng cổng đó. Với PostgreSQL, đổi `POSTGRES_PORT` trong `.env` (ví dụ `5433`). Nếu đang chạy Cách B thì tắt cửa sổ backend/frontend local trước khi chạy Cách A. |
| `could not select device driver "nvidia"` | Máy không có GPU NVIDIA: chạy lệnh mặc định, không thêm `docker-compose.gpu.yml`. |
| Trợ lý AI phản hồi chậm hoặc không trả lời | Model đang tải hoặc chạy bằng CPU. Kiểm tra bằng `docker compose logs ollama-pull`. Khi AI không sẵn sàng, hệ thống dùng chế độ gợi ý dự phòng (rule-based). |
| Backend báo `exec ./docker-entrypoint.sh: no such file or directory` | File `.sh` bị đổi sang định dạng xuống dòng Windows (CRLF). Repo đã cấu hình `.gitattributes` và Dockerfile để tự xử lý; nếu vẫn gặp, chạy `docker compose build --no-cache backend`. |
| Tải image bị lỗi `unexpected EOF` | Mạng chập chờn khi tải image, chạy lại lệnh `docker compose up -d --build`. |

---

## 📜 Giấy phép Mã nguồn mở

Dự án được phân phối dưới giấy phép [MIT License](LICENSE).
