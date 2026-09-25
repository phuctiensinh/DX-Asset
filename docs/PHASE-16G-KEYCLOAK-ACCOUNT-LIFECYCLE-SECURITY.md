# PHASE 16G — KEYCLOAK USER LIFECYCLE & ACCOUNT SECURITY

## 1. MỤC TIÊU & TỔNG QUAN

Phase 16G hoàn thiện toàn bộ vòng đời (Lifecycle) và bảo mật tài khoản (Security) giữa **Keycloak OIDC Identity Provider** và **DX-Asset Platform**. 

Phase 16G đảm bảo rằng:
- **Xác thực (Authentication)** được quản lý tập trung và tin cậy bởi Keycloak OIDC (PKCE flow).
- **Phân quyền (Authorization)** duy trì nguồn sự thật duy nhất (**Source of Truth**) là bảng `users.role` trong **PostgreSQL**.
- Toàn bộ quy trình đăng ký JIT, identity linking, logout, refresh token, tài khoản bị vô hiệu hóa (disabled account) và kiểm toán bảo mật hoạt động an toàn, chính xác và được kiểm thử tự động.

---

## 2. VÒNG ĐỜI TÀI KHOẢN (ACCOUNT LIFECYCLE)

Hệ thống xác định rõ 4 kịch bản vòng đời tài khoản khi người dùng tương tác qua Keycloak:

### Kịch bản A: User đăng ký mới trên Keycloak (JIT Provisioning)
1. Người dùng đăng ký tài khoản mới trên Keycloak Server.
2. Đăng nhập vào DX-Asset thông qua OIDC Authorization Code Flow (PKCE).
3. Backend kiểm tra qua `get_current_user`: nhận diện chưa có bản ghi local dựa trên Keycloak `sub` và `email`.
4. Backend tự động khởi tạo (JIT Provisioning) bản ghi `User` mới trong PostgreSQL:
   - `keycloak_user_id = sub`
   - `email = email`
   - `role = UserRole.EMPLOYEE` (Mặc định cho người dùng mới)
   - `is_active = True`

### Kịch bản B: User đã tồn tại trong PostgreSQL nhưng chưa có `keycloak_user_id` (First-time Identity Linking)
1. Người dùng đã tồn tại trong PostgreSQL từ trước (ví dụ tài khoản seeded).
2. Đăng nhập qua Keycloak với cùng địa chỉ `email`.
3. Backend phát hiện email khớp nhưng `keycloak_user_id` đang rỗng (`None`).
4. Backend liên kết an toàn bằng cách cập nhật `keycloak_user_id = sub`.
5. **Giữ nguyên vai trò (`users.role`) hiện tại** trong PostgreSQL (Không bị ghi đè hay thay đổi thành `EMPLOYEE`).

### Kịch bản C: User đã được liên kết (`keycloak_user_id` đã được gán)
1. Trong các lần đăng nhập tiếp theo, Backend thực hiện truy vấn nhanh dựa trên chỉ mục `keycloak_user_id == sub` (Indexed lookup).
2. Không tạo bản ghi trùng lặp (Duplicate user).
3. Giữ nguyên vai trò `users.role` hiện tại từ PostgreSQL.

### Kịch bản D: Xung đột định danh (Identity Conflict Protection)
1. Một token chứa `sub` A cố truy cập vào tài khoản có `email` X nhưng trong DB `email` X đã được liên kết với `sub` B khác.
2. Backend phát hiện xung đột định danh, ghi log cảnh báo và từ chối truy cập với lỗi **401 Unauthorized**.

---

## 3. NGUỒN SỰ THẬT VỀ VAI TRÒ (ROLE SOURCE OF TRUTH INVARIANT)

- **Nguyên tắc cốt lõi**: Cơ sở dữ liệu **PostgreSQL `users.role`** là nguồn duy nhất quyết định quyền hạn nghiệp vụ của người dùng.
- **Không tự động nâng quyền**: Hệ thống tuyệt đối KHÔNG tự động nâng hay đổi vai trò người dùng dựa trên:
  - Keycloak Realm / Client Roles.
  - Claims trong JWT token.
  - Groups hoặc Email Domain.
- **Strict Prohibition**: Bất kỳ token nào cố tình khai gian claim `role: "ADMIN"` trong JWT đều bị Backend bỏ qua và đánh giá quyền dựa trên bản ghi thực tế trong PostgreSQL (`403 Forbidden`).

---

## 4. XỬ LÝ ĐĂNG XUẤT (LOGOUT BEHAVIOR & SESSION CLEANUP)

- Khi người dùng chọn **Đăng xuất**:
  1. Frontend gọi `clearStoredTokens()`, xóa sạch `dx_asset_access_token` và `dx_asset_refresh_token` trong `localStorage`.
  2. State người dùng (`user`) trong `AuthContext` được đặt lại về `null`.
  3. Frontend kích hoạt `logoutKeycloak()`, điều hướng trình duyệt tới Keycloak OIDC Logout endpoint (`/realms/dx-asset/protocol/openid-connect/logout`) với `post_logout_redirect_uri`.
  4. Session SSO tại Keycloak Server được chấm dứt và trình duyệt được chuyển hướng về trang `/login`.
  5. Mọi nỗ lực truy cập protected routes sau khi đăng xuất đều bị chặn và yêu cầu đăng nhập lại (HTTP 401).
- **Client Secret**: Trình duyệt frontend sử dụng OIDC Public Client (PKCE), không lưu trữ hay làm lộ Keycloak Client Secret.

---

## 5. XỬ LÝ REFRESH TOKEN & CHỐNG RACE CONDITION

Audit cơ chế làm mới token từ Phase 16E:
- **Proactive Refresh**: Frontend kiểm tra thời gian hết hạn của token trước khi thực hiện API request. Nếu token sắp/đã hết hạn, kích hoạt `refreshAccessToken()`.
- **Reactive Refresh**: Nếu Backend phản hồi **401 Unauthorized**, Frontend thử làm mới token một lần và tự động retry request.
- **Khóa làm mới đơn lẻ (Single Inflight Promise Lock)**: 
  Đã bổ sung cơ chế `refreshPromise` trong `frontend/src/lib/oidc.ts`. Khi nhiều request API diễn ra đồng thời cùng gặp lỗi 401/expired:
  - Chỉ duy nhất 1 yêu cầu refresh token được gửi tới Keycloak.
  - Các request còn lại cùng chờ kết quả từ `refreshPromise` shared, tránh việc gửi hàng loạt yêu cầu refresh token làm thu hồi refresh token hợp lệ (Refresh Token Rotation race condition).
- **Refresh thất bại**: Nếu refresh token bị hết hạn hoặc không hợp lệ, toàn bộ session local lập tức bị xóa sạch và người dùng được chuyển hướng về trang đăng nhập.

---

## 6. QUẢN LÝ TÀI KHOẢN BỊ VÔ HIỆU HÓA (DISABLED ACCOUNT)

- **Trong PostgreSQL**: Mọi API request Backend đều kiểm tra `user.is_active` thông qua `get_current_user`. Nếu `is_active == False`, Backend lập tức trả về **401 Unauthorized** ("User account is inactive").
- **Hạn chế đã biết (Known Limitation)**:
  - DX-Asset xác thực JWT stateless thông qua chữ ký mã hóa (JWKS) và dựa vào PostgreSQL `users.is_active` để quản lý trạng thái kích hoạt cục bộ.
  - DX-Asset không thực hiện HTTP back-channel polling tới Keycloak trên từng request đơn lẻ.
  - Nếu một người dùng bị disabled trên Keycloak nhưng vẫn sở hữu Access Token cũ chưa hết hạn, người dùng vẫn có thể truy cập ngắn hạn cho đến khi Access Token đó hết hạn (hoặc cho đến khi yêu cầu refresh token bị Keycloak từ chối).

---

## 7. KIỂM TOÁN BẢO MẬT (SECURITY AUDIT CHECKLIST)

| Hạng mục kiểm tra | Trạng thái | Ghi chú |
| :--- | :--- | :--- |
| Không tin tưởng `role` trong JWT | **PASSED** | Backend luôn đọc `users.role` từ PostgreSQL |
| Ngăn nâng quyền thành `ADMIN` | **PASSED** | Chỉ duy nhất System Owner được giữ vai trò `ADMIN` |
| Không làm lộ Keycloak Client Secret | **PASSED** | Frontend sử dụng OIDC Public Client với PKCE |
| Không lưu mật khẩu Keycloak ở DB local | **PASSED** | Lưu chuỗi đánh dấu `EXTERNAL_KEYCLOAK_AUTHENTICATED` |
| Không ghi log sensitive tokens | **PASSED** | Log không chứa `access_token`, `refresh_token`, hay `Authorization` header |
| Không làm lộ Refresh Token ở API | **PASSED** | Token chỉ giao tiếp giữa client và Keycloak OIDC endpoint |
| Bảo vệ System Owner | **PASSED** | Không thể demote hay hạ quyền System Owner |
| CORS Configuration | **PASSED** | Được cấu hình hợp lệ qua Middleware |

---

## 8. BẢO TỒN DỮ LIỆU & TOÀN VẸN DATABASE (DATABASE INTEGRITY)

- **Migration Status**: Không có migration mới nào được tạo trong Phase 16G.
- **Bảo tồn các bảng nghiệp vụ**:
  - `users` (Role source of truth)
  - `assets`
  - `asset_assignments`
  - `incidents`
  - `maintenances`
  - `process_cases`
  - `process_events`
  - `asset_histories`

---

## 9. KẾT QUẢ KIỂM THỬ (TEST RESULTS)

### 9.1. Backend Pytest Suite

```bash
backend\.venv\Scripts\pytest.exe
```
**Kết quả**: **189 / 189 tests PASSED (100% Success)**

Bao gồm đầy đủ các kịch bản:
1. New Keycloak user → JIT creation local EMPLOYEE.
2. Existing local user → First-time identity linking keycloak_user_id.
3. Existing linked user → Fast indexed lookup by sub, không tạo duplicate.
4. Fake role claim in JWT → Bị từ chối nâng quyền (403/401).
5. Identity conflict → Bị từ chối (401).
6. Non-admin truy cập `/users` → 403 Forbidden.
7. Protected API không có token / expired token → 401 Unauthorized.
8. Inactive / Disabled local user → 401 Unauthorized.
9. System Owner protection & Admin creation restriction.

### 9.2. Frontend TypeScript & Next.js Build

```bash
npx tsc --noEmit
npm run build
```
**Kết quả**:
- TypeScript typecheck: **0 errors**.
- Next.js build: **16/16 static & dynamic pages compiled successfully** (bao gồm `/login`, `/auth/callback`, `/dashboard`, `/users`).

---

## 10. TRẠNG THÁI HOÀN THÀNH

```text
PHASE 16G STATUS: COMPLETE
```
