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
- **Trợ lý AI chạy cục bộ (Human-in-the-loop)**: Ollama gợi ý phân loại & độ ưu tiên sự cố, tóm tắt sự cố và vòng đời tài sản, giải thích rủi ro tài sản, viết báo cáo phân tích quy trình. AI chỉ gợi ý; khi Ollama không sẵn sàng hệ thống tự dùng kết quả dự phòng theo quy tắc.

---

## 🏛️ Ánh xạ Kiến trúc 4 Không gian DX-OS (H-P-D-I)

- **[H] Human (Nhân sự)**: Quản trị định danh tập trung (4 vai trò: `ADMIN`, `IT_ASSET_MANAGER`, `EMPLOYEE`, `MANAGER`), quản lý người dùng và phòng ban.
- **[P] Process (Quy trình)**: Luồng Cấp phát $\rightarrow$ Thu hồi $\rightarrow$ Báo hỏng $\rightarrow$ Bảo trì khép kín, thiết lập ràng buộc trạng thái thiết bị hợp lệ (Poka-yoke).
- **[D] Data (Dữ liệu)**: Lưu trữ tập trung PostgreSQL (Single Source of Truth), bảo lưu lịch sử Timeline, hiển thị Dashboard thời gian thực.
- **[I] Intelligence (AI)**: Backend tính điểm rủi ro tài sản, khai phá quy trình (Process Mining) và mô phỏng What-if bằng thuật toán minh bạch; Ollama chạy cục bộ diễn giải các kết quả đó và gợi ý phân loại sự cố, hỗ trợ con người ra quyết định.

---

## 🤖 Tính năng AI (Ollama, chạy cục bộ)

AI chạy bằng model `qwen2.5:3b` trên chính máy chủ (Ollama), không gửi dữ liệu ra ngoài. AI **chỉ gợi ý**, không tự lưu hay thay đổi dữ liệu.

| Tính năng | Ở đâu | Ai dùng được |
|---|---|---|
| Gợi ý phân loại & mức ưu tiên khi báo hỏng | Form "Báo cáo sự cố" → nút **Gợi ý bằng AI** → **Áp dụng gợi ý** | Mọi người dùng |
| Tóm tắt sự cố | Chi tiết sự cố → **Trợ lý AI** → **Tóm tắt sự cố** | Người xem được phiếu (nhân viên chỉ với phiếu của mình) |
| Gợi ý các bước xử lý (dựa trên sự cố tương tự đã giải quyết) | Chi tiết sự cố → **Gợi ý các bước xử lý** | ADMIN, IT_ASSET_MANAGER |
| Phân loại queue xử lý | API `POST /incidents/{id}/classify` | ADMIN, IT_ASSET_MANAGER |
| Giải thích rủi ro tài sản (vì sao điểm rủi ro cao, 1–2 khuyến nghị) | Chi tiết tài sản → **AI giải thích rủi ro** (`POST /intelligence/assets/{id}/ai/explain`) | ADMIN, IT_ASSET_MANAGER, MANAGER; nhân viên chỉ với tài sản đang giữ |
| Tóm tắt vòng đời tài sản (cấp phát, sự cố, bảo trì, chi phí, bảo hành) | Chi tiết tài sản → **Tóm tắt vòng đời bằng AI** (`POST /assets/{id}/ai/summary`) | ADMIN, IT_ASSET_MANAGER, MANAGER; nhân viên chỉ với tài sản đang giữ |
| Báo cáo phân tích quy trình (tổng quan, điểm nghẽn, làm lại, tuân thủ, tối đa 3 đề xuất) | Trang **Phân tích quy trình** → **Tạo báo cáo AI** (`POST /process-mining/ai/report`, theo bộ lọc đang chọn) | ADMIN, IT_ASSET_MANAGER, MANAGER |
| Trợ lý hỏi đáp dữ liệu | Trang **Trợ lý AI** | Theo vai trò |

- Khi Ollama tắt, quá chậm hoặc trả kết quả sai định dạng, hệ thống tự dùng **phương án dự phòng theo quy tắc**. Giao diện ghi rõ kết quả đến từ **AI (Ollama)** hay **Dự phòng theo quy tắc** / **Phân tích dự phòng**.
- Với giải thích rủi ro, tóm tắt vòng đời và báo cáo quy trình, AI chỉ **diễn giải số liệu backend đã tính** (điểm rủi ro, lịch sử, kết quả Process Mining) trong phạm vi người dùng được phép xem; câu trả lời chứa con số không có trong dữ liệu đầu vào bị loại và thay bằng kết quả dự phòng.
- Các tính năng AI trên giao diện chỉ chạy khi người dùng bấm nút; kết quả không được lưu vào cơ sở dữ liệu.
- Lần gọi đầu tiên sau khi khởi động cần nạp model (khoảng 10–15 giây với GPU, lâu hơn với CPU). Các lần sau với GPU chỉ khoảng 1–3 giây.
- Cấu hình trong `.env`: `OLLAMA_ENABLED`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`.

---

## 🛠️ Công nghệ Sử dụng

- **Frontend**: Next.js 14 (App Router), TypeScript 5, Tailwind CSS, shadcn/ui.
- **Backend**: Python 3.12, FastAPI 0.111, Pydantic v2, SQLAlchemy 2.0, Alembic (Migration).
- **Database**: PostgreSQL 16.
- **AI**: Ollama chạy cục bộ trong Docker, model `qwen2.5:3b` (đổi được qua `OLLAMA_MODEL`).
- **Dịch vụ đi kèm**: Keycloak (đăng nhập/định danh), SeaweedFS (lưu ảnh đính kèm sự cố).
- **Containerization**: Docker & Docker Compose v2.

---

## 🚀 Hướng dẫn Cài đặt & Chạy ứng dụng

Có 2 cách chạy. **Cách A (Docker)** là cách khuyến nghị cho người mới clone về: chỉ cần cài Docker, không cần cài Python hay Node.js.

### Yêu cầu máy

- Hệ điều hành: **Windows 10 (bản 21H2 trở lên) / Windows 11**, **macOS 12 trở lên**, hoặc **Ubuntu 22.04 / Debian 12 trở lên**.
- RAM trống tối thiểu ~6 GB, ổ đĩa trống ~10 GB (gồm Docker, các image và model AI `qwen2.5:3b` ~1.9 GB).
- Có kết nối Internet ở lần cài đầu tiên.
- Windows: cần bật **ảo hóa (Virtualization)** trong BIOS. Hầu hết máy đời mới đã bật sẵn; kiểm tra ở *Task Manager → Performance → CPU → Virtualization: Enabled*.

Không cần cài Python, Node.js hay PostgreSQL: mọi thứ chạy trong Docker. Bước 0 dưới đây cài sẵn **Git** và **Docker** nếu máy chưa có.

---

### Cách A — Chạy toàn bộ bằng Docker (khuyến nghị)

#### Bước 0: Cài Git và Docker (chỉ làm một lần trên mỗi máy)

Máy đã có Git và Docker thì bỏ qua bước này. Kiểm tra bằng:
```bash
git --version
```
```bash
docker compose version
```

<details open>
<summary><b>Windows 10/11</b></summary>

1. Mở **PowerShell bằng quyền Administrator**: bấm nút Start, gõ `PowerShell`, chuột phải → *Run as administrator*.
2. Chạy lần lượt 3 lệnh (đồng ý khi được hỏi):
   ```powershell
   wsl --install
   ```
   ```powershell
   winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
   ```
   ```powershell
   winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
   ```
   - `wsl --install` cài nền Linux (WSL 2) mà Docker Desktop cần. Nếu máy báo WSL đã có sẵn thì tiếp tục bình thường.
   - Nếu báo không có lệnh `winget`: mở Microsoft Store, cài/cập nhật ứng dụng **App Installer**, rồi chạy lại.
3. **Khởi động lại máy** (bắt buộc, để WSL và Docker hoạt động).
4. Mở **Docker Desktop** từ menu Start. Lần đầu bấm **Accept** điều khoản, có thể chọn *Skip* phần đăng nhập/khảo sát. Đợi đến khi góc dưới bên trái hiện **Engine running**.
5. Mở **PowerShell mới** (không cần quyền Administrator) và kiểm tra:
   ```powershell
   git --version
   ```
   ```powershell
   docker compose version
   ```

</details>

<details>
<summary><b>macOS</b></summary>

1. Mở ứng dụng **Terminal**, cài Homebrew (nếu chưa có) theo lệnh chính thức tại https://brew.sh:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   Làm theo các dòng *Next steps* mà trình cài in ra ở cuối (thêm `brew` vào PATH).
2. Cài Git và Docker Desktop:
   ```bash
   brew install git
   ```
   ```bash
   brew install --cask docker
   ```
3. Mở Docker Desktop, bấm **Accept** điều khoản và đợi đến khi hiện **Engine running**:
   ```bash
   open -a Docker
   ```

</details>

<details>
<summary><b>Ubuntu / Debian</b></summary>

1. Cài Git và Docker Engine (kèm Docker Compose) bằng script chính thức của Docker:
   ```bash
   sudo apt-get update && sudo apt-get install -y git curl
   ```
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   ```
2. Cho phép tài khoản hiện tại dùng Docker không cần `sudo`, rồi **đăng xuất và đăng nhập lại**:
   ```bash
   sudo usermod -aG docker $USER
   ```

</details>

#### Bước 1: Tải mã nguồn

```bash
git clone https://github.com/phuctiensinh/DX-Asset.git
```
```bash
cd DX-Asset
```

#### Bước 2: Tạo file cấu hình `.env`

Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```
macOS / Linux:
```bash
cp .env.example .env
```
Giữ nguyên các giá trị mặc định là chạy được trên máy cá nhân. Khi triển khai thật, **bắt buộc** đổi `SECRET_KEY`, `POSTGRES_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`.

#### Bước 3: Build và khởi động

Docker Desktop phải đang chạy (**Engine running**). Sau đó:
```bash
docker compose up -d --build
```
Lần đầu mất khoảng **5–15 phút** tùy tốc độ mạng (tải image, build frontend/backend). Backend tự chạy migration và nạp dữ liệu mẫu. Model AI (~1.9 GB) được tải ngầm sau đó; trong lúc chờ, hệ thống vẫn dùng được và các tính năng AI tạm dùng chế độ dự phòng theo quy tắc.

#### Bước 4: Kiểm tra hệ thống đã sẵn sàng

```bash
docker compose ps -a
```
Các dịch vụ `dx_asset_postgres`, `dx_asset_keycloak`, `dx_asset_seaweedfs`, `dx_asset_ollama` phải ở trạng thái `healthy`; `dx_asset_backend` và `dx_asset_frontend` ở trạng thái `Up`. Riêng `dx_asset_ollama_pull` (job tải model AI) chạy xong sẽ là `Exited (0)` — đó là bình thường.

Nếu vừa chạy xong mà backend chưa lên, đợi thêm 1–2 phút (Keycloak khởi động chậm ở lần đầu) rồi chạy lại lệnh kiểm tra.

#### Bước 5: Mở ứng dụng và tạo tài khoản

1. Mở trình duyệt vào **http://localhost:3000**.
2. Bấm **Đăng ký tài khoản mới**, điền thông tin và bấm **Đăng ký**. Hệ thống tự đăng nhập và đưa bạn vào trang Tổng quan với vai trò Nhân viên.
3. Muốn dùng quyền Quản trị viên: xem mục [Tài khoản đăng nhập](#tài-khoản-đăng-nhập).

| Dịch vụ | Địa chỉ |
|---|---|
| Ứng dụng web | http://localhost:3000 |
| Tài liệu API (Swagger) | http://localhost:8000/docs |
| Trang quản trị Keycloak | http://localhost:8080 (tài khoản lấy từ `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD` trong `.env`) |

> ⚠️ Luôn truy cập bằng `localhost`, **không** dùng `127.0.0.1` hay IP máy. Phiên đăng nhập gắn với địa chỉ `localhost`; dùng địa chỉ khác sẽ bị lỗi 401.

Những lần sau chỉ cần mở Docker Desktop rồi chạy `docker compose up -d` trong thư mục `DX-Asset`.

#### Dùng GPU NVIDIA cho AI (tùy chọn)

Mặc định Ollama chạy bằng CPU để chạy được trên mọi máy. Nếu máy có card NVIDIA:
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

---

### Cách B — Chạy dev local (dành cho người phát triển)

Backend và frontend chạy trực tiếp trên máy (có hot-reload); các dịch vụ hạ tầng chạy bằng Docker. Script `start-dev.bat` dành cho **Windows**.

0. Làm **Bước 0 và Bước 1 của Cách A** (cài Git, Docker, tải mã nguồn), rồi cài thêm Python 3.12 và Node.js trong PowerShell:
   ```powershell
   winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
   ```
   ```powershell
   winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
   ```
   Sau khi cài, **mở PowerShell mới** để nhận lệnh `python` và `npm`.
1. Tạo file môi trường (PowerShell):
   ```powershell
   Copy-Item .env.example .env
   ```
   ```powershell
   Copy-Item frontend/.env.local.example frontend/.env.local
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

- **Người dùng mới**: tại trang đăng nhập, bấm **"Đăng ký tài khoản mới"**, điền thông tin rồi bấm **Đăng ký**. Sau khi đăng ký, hệ thống tự đăng nhập và tạo tài khoản với vai trò Nhân viên.
- **Quản trị viên (ADMIN)**: hệ thống chỉ cho phép **một** tài khoản ADMIN duy nhất (System Owner), gắn với email `2424801030008@student.tdmu.edu.vn`. Đăng ký Keycloak bằng đúng email này sẽ được liên kết với tài khoản ADMIN có sẵn trong dữ liệu mẫu.
- ADMIN có thể đổi vai trò người dùng khác (`IT_ASSET_MANAGER`, `MANAGER`, `EMPLOYEE`) tại trang **Người dùng**.

---

### Giao diện tiếng Việt cho trang đăng nhập (Keycloak)

Keycloak 24 không có sẵn tiếng Việt, nên dự án kèm theme `docker/keycloak/themes/dx-asset` với bản dịch tiếng Việt. Cài mới bằng `docker compose up -d --build` thì theme được bật tự động.

Nếu Keycloak trên máy bạn đã được tạo **trước** khi có theme này, chạy 2 lệnh sau một lần để bật tiếng Việt (không ảnh hưởng tài khoản đã có):

```bash
docker compose up -d keycloak
```

```bash
docker exec dx_asset_keycloak sh -c '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user "$KEYCLOAK_ADMIN" --password "$KEYCLOAK_ADMIN_PASSWORD" && /opt/keycloak/bin/kcadm.sh update realms/dx-asset -s loginTheme=dx-asset -s internationalizationEnabled=true -s "supportedLocales=[\"vi\"]" -s defaultLocale=vi'
```

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
| `git` hoặc `docker` báo *not recognized / command not found* ngay sau khi cài | Cửa sổ terminal cũ chưa nhận đường dẫn mới. Đóng và mở lại PowerShell/Terminal. |
| `error during connect` hoặc `dockerDesktopLinuxEngine: The system cannot find the file specified` | Docker Desktop chưa chạy. Mở Docker Desktop, đợi hiện **Engine running** rồi chạy lại lệnh. |
| Docker Desktop báo *WSL 2 is not installed* hoặc *Virtualization support not detected* | Chạy `wsl --install` trong PowerShell (Administrator), khởi động lại máy. Nếu vẫn lỗi, bật **Virtualization (Intel VT-x / AMD-V)** trong BIOS. |
| Linux báo *permission denied … docker.sock* | Chưa đăng xuất/đăng nhập lại sau lệnh `usermod -aG docker`. Đăng xuất rồi đăng nhập lại (hoặc khởi động lại máy). |
| Đăng nhập/đăng ký xong bị quay về trang Login, console báo `401` ở `/auth/me` | Truy cập bằng `localhost:3000` (không dùng `127.0.0.1`). Xóa Local Storage của trang (F12 → Application → Local Storage) rồi thử lại. Xem lý do cụ thể bằng `docker compose logs backend`. Nếu Keycloak vừa khởi động, đợi ~1 phút. |
| `port is already allocated` (5432, 8080, 3000, 8000…) | Có chương trình khác đang dùng cổng đó. Với PostgreSQL, đổi `POSTGRES_PORT` trong `.env` (ví dụ `5433`). Nếu đang chạy Cách B thì tắt cửa sổ backend/frontend local trước khi chạy Cách A. |
| `could not select device driver "nvidia"` | Máy không có GPU NVIDIA: chạy lệnh mặc định, không thêm `docker-compose.gpu.yml`. |
| Trợ lý AI phản hồi chậm hoặc không trả lời | Model đang tải hoặc chạy bằng CPU. Kiểm tra bằng `docker compose logs ollama-pull`. Khi AI không sẵn sàng, hệ thống dùng chế độ gợi ý dự phòng (rule-based). |
| Backend báo `exec ./docker-entrypoint.sh: no such file or directory` | File `.sh` bị đổi sang định dạng xuống dòng Windows (CRLF). Repo đã cấu hình `.gitattributes` và Dockerfile để tự xử lý; nếu vẫn gặp, chạy `docker compose build --no-cache backend`. |
| Tải image bị lỗi `unexpected EOF` | Mạng chập chờn khi tải image, chạy lại lệnh `docker compose up -d --build`. |

---

## 📜 Giấy phép Mã nguồn mở

Dự án được phân phối dưới giấy phép [MIT License](LICENSE).
