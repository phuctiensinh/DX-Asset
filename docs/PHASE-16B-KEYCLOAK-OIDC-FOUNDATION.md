# BÁO CÁO TRIỂN KHAI DOCKER KEYCLOAK & NỀN TẢNG OIDC (PHASE 16B)

**Dự án:** DX-Asset: Open-Source Digital Asset Lifecycle Management Platform  
**Tác giả:** Nguyễn Phạm Đại Phúc (Trường Đại học Thủ Dầu Một)  
**Ngày thực hiện:** 25/09/2026  
**Trạng thái Phase 16B:** `COMPLETE`

---

## 1. PHIÊN BẢN KEYCLOAK & CẤU HÌNH DOCKER

### 1.1 Phiên bản Keycloak Pinned
- **Image**: `quay.io/keycloak/keycloak:24.0.5`
- **Lý do lựa chọn**: Phiên bản ổn định chính thức (Stable Release), tương thích hoàn hảo với Java Quarkus runtime và PostgreSQL 16. Ghim phiên bản cố định giúp quá trình build reproducible, tránh rủi ro vỡ cấu hình khi dùng tag `:latest`.

### 1.2 Cấu hình Docker Compose (`docker-compose.yml`)
Keycloak được thêm vào danh sách dịch vụ Docker Compose với các thiết lập bảo đảm cách ly dữ liệu:
- **Service Name**: `keycloak`
- **Container Name**: `dx_asset_keycloak`
- **Host Port**: `8080:8080`
- **Biến môi trường Quản trị**:
  - `KEYCLOAK_ADMIN=admin`
  - `KEYCLOAK_ADMIN_PASSWORD=admin_password_secret`
- **Biến môi trường Cấu hình Runtime**:
  - `KC_DB=postgres`
  - `KC_DB_URL=jdbc:postgresql://postgres:5432/keycloak_db`
  - `KC_DB_USERNAME=dx_user`
  - `KC_DB_PASSWORD=dx_password_secret`
  - `KC_HTTP_ENABLED=true`
  - `KC_HOSTNAME_STRICT=false`
  - `KC_HEALTH_ENABLED=true`
- **Command khởi chạy**: `start-dev --import-realm`

---

## 2. CÁCH LY CƠ SỞ DỮ LIỆU (DATABASE ISOLATION)

Theo đúng quy tắc **bảo mật dữ liệu tuyệt đối** của Phase 16B:
- Keycloak kết nối tới cơ sở dữ liệu riêng biệt `keycloak_db` trên cùng container `dx_asset_postgres`.
- Keycloak **HOÀN TOÀN KHÔNG SỬ DỤNG** và không tạo bất kỳ bảng nào trong cơ sở dữ liệu nghiệp vụ `dx_asset_db`.
- Script tự động khởi tạo database [docker/postgres/init-keycloak-db.sql](file:///D:/web/dx-asset/docker/postgres/init-keycloak-db.sql):
  ```sql
  SELECT 'CREATE DATABASE keycloak_db'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak_db')\gexec
  ```

---

## 3. CẤU HÌNH REALM & OIDC CLIENT (`realm-export.json`)

File khởi tạo tự động [docker/keycloak/realm-export.json](file:///D:/web/dx-asset/docker/keycloak/realm-export.json) được mount trực tiếp vào container Keycloak `/opt/keycloak/data/import/realm-export.json`:

### 3.1 Cấu hình Realm `dx-asset`
- **Realm ID / Name**: `dx-asset`
- **Display Name**: DX-Asset Digital Asset Lifecycle Management
- **Self-Registration**: `registrationAllowed: true` (Cho phép người dùng mới tự đăng ký).
- **Email Verification**: `verifyEmail: false` (Tắt xác minh email trong môi trường local dev để thuận tiện kiểm thử).
- **Thuật toán chữ ký mặc định**: `RS256`

### 3.2 Cấu hình OIDC Client `dx-asset-frontend`
- **Client ID**: `dx-asset-frontend`
- **Client Type**: Public (Standard Authorization Code Flow with PKCE enabled).
- **Valid Redirect URIs**:
  - `http://localhost:3000/*`
  - `http://127.0.0.1:3000/*`
- **Web Origins (CORS)**:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
- **Direct Access Grants (Resource Owner Password Flow)**: Bật trong môi trường dev để phục vụ các script kiểm thử tự động cấp Token.

---

## 4. KẾT QUẢ KIỂM THỬ XÁC MINH OIDC FOUNDATION

### 4.1 OIDC Discovery Endpoint
- **URL**: `http://localhost:8080/realms/dx-asset/.well-known/openid-configuration`
- **HTTP Status Code**: `200 OK`
- **Các thông số Discovery đã xác minh**:
  - `issuer`: `http://localhost:8080/realms/dx-asset`
  - `authorization_endpoint`: `http://localhost:8080/realms/dx-asset/protocol/openid-connect/auth`
  - `token_endpoint`: `http://localhost:8080/realms/dx-asset/protocol/openid-connect/token`
  - `jwks_uri`: `http://localhost:8080/realms/dx-asset/protocol/openid-connect/certs`

### 4.2 JWKS Endpoint & Chữ ký RS256
- **URL**: `http://localhost:8080/realms/dx-asset/protocol/openid-connect/certs`
- **HTTP Status Code**: `200 OK`
- **Kết quả xác minh khóa Khóa công khai (Public Key)**:
  - Số lượng khóa: `2`
  - Thuật toán chữ ký: `RS256`
  - Key ID (`kid`): `4o3BgRHeG4TIionjH9nHTPTE2iUNPbp6BE_KMjq5aLA`

### 4.3 Test User Login & Cấp Token
- **Tài khoản Test**: `testuser` / Email: `testuser@student.tdmu.edu.vn` / Password: `password123`
- **Kết quả gửi request tới Token Endpoint**:
  - **HTTP Status Code**: `200 OK`
  - **Access Token**: Đã được phát thành công (`HAS ACCESS TOKEN: True`)
  - **Token Type**: `Bearer`
  - **Thời gian hiệu lực**: `300` giây (5 phút)

---

## 5. DATABASE SAFETY CHECK (KIỂM TRA AN TOÀN DỮ LIỆU CƠ SỞ DỮ LIỆU)

Số lượng bản ghi trong cơ sở dữ liệu `dx_asset_db` được so sánh đối chiếu trước và sau khi triển khai Keycloak Container:

| Bảng dữ liệu | Số bản ghi Trước khi chạy Keycloak | Số bản ghi Sau khi chạy Keycloak | Trạng thái |
| :--- | :--- | :--- | :--- |
| `users` | 5 | 5 | ✅ KHÔNG ĐỔI |
| `assets` | 907 | 907 | ✅ KHÔNG ĐỔI |
| `asset_assignments` | 218 | 218 | ✅ KHÔNG ĐỔI |
| `incidents` | 10 | 10 | ✅ KHÔNG ĐỔI |
| `maintenances` | 8 | 8 | ✅ KHÔNG ĐỔI |
| `asset_histories` | 863 | 863 | ✅ KHÔNG ĐỔI |
| `process_cases` | 15 | 15 | ✅ KHÔNG ĐỔI |
| `process_events` | 33 | 33 | ✅ KHÔNG ĐỔI |
| `technician_skills` | 1 | 1 | ✅ KHÔNG ĐỔI |

> **KẾT LUẬN AN TOÀN:** Keycloak chạy hoàn toàn độc lập trong database `keycloak_db`. Không có bất kỳ sự thay đổi hay ảnh hưởng ngoài dự kiến nào tới cơ sở dữ liệu `dx_asset_db`.

---

## 6. DANH SÁCH FILE THAY ĐỔI VÀ KHÔNG THAY ĐỔI

### 6.1 Các File đã Thay đổi / Tạo mới:
1. `docker-compose.yml`: Bổ sung service `keycloak` và mount init script cho `postgres`.
2. `docker/postgres/init-keycloak-db.sql`: Tạo script khởi tạo database `keycloak_db`.
3. `docker/keycloak/realm-export.json`: Cấu hình Realm `dx-asset`, Client `dx-asset-frontend` và User `testuser`.
4. `docs/PHASE-16B-KEYCLOAK-OIDC-FOUNDATION.md`: File báo cáo hoàn tất Phase 16B.

### 6.2 Các File Cố ý KHÔNG Thay đổi (Intentionally Unchanged):
- Mã nguồn FastAPI Backend (`app/core/security.py`, `app/api/deps.py`, `app/api/v1/auth.py`,...).
- Mã nguồn Next.js Frontend (`auth-context.tsx`, `api.ts`, `/login`,...).
- Alembic DB Migrations và Schema của `users`.
- Bộ unit test Backend (`pytest` đã chạy lại và đạt **165/165 passed 100%**).

---

## 7. KHUYẾT ĐIỂM HẠN CHẾ & YÊU CẦU PHASE TIẾP THEO

### 7.1 Hạn chế Hiện tại của Phase 16B
- Phase 16B mới chỉ dựng hạ tầng Keycloak Docker độc lập. FastAPI Backend và Frontend Next.js hiện vẫn đang dùng cơ chế JWT mã hóa đối xứng nội bộ cũ.

### 7.2 Yêu cầu đối với Phase 16C
- Triển khai xác thực JWT chữ ký RS256 trên FastAPI Backend bằng cách tích hợp Keycloak JWKS Client vào `app/core/security.py` và `app/api/deps.py`.

---

## 8. ACCEPTANCE CRITERIA CHECKLIST

- [x] Keycloak chạy thành công bằng Docker Compose
- [x] Phiên bản Keycloak được ghim cố định (`24.0.5`)
- [x] Keycloak không sử dụng cơ sở dữ liệu `dx_asset_db`
- [x] Realm `dx-asset` được tạo tự động khi container khởi chạy
- [x] Client OIDC `dx-asset-frontend` tồn tại
- [x] Authorization Code Flow & PKCE được cấu hình sẵn
- [x] Redirect URIs hợp lệ (`http://localhost:3000/*`)
- [x] Self-registration được bật
- [x] Không cho phép người dùng tự chọn vai trò nghiệp vụ DX-Asset khi đăng ký
- [x] Endpoint OIDC Discovery trả về `200 OK`
- [x] Endpoint JWKS trả về `200 OK` với thuật toán RS256 và `kid`
- [x] Tài khoản `testuser` đăng nhập và được phát Access Token thành công
- [x] Cơ sở dữ liệu PostgreSQL `dx_asset_db` giữ nguyên 100%
- [x] Authentication cũ của FastAPI giữ nguyên
- [x] Authentication cũ của Frontend giữ nguyên
- [x] Không tạo DB Migration nào cho DX-Asset ở Phase 16B
- [x] Toàn bộ 165 backend unit tests chạy đạt 100% PASS
- [x] Không thực hiện `git commit` hoặc `git push`

---

```text
PHASE 16B STATUS: COMPLETE
```
