# PHASE 16J — FINAL KEYCLOAK INTEGRATION & RELEASE VERIFICATION

**Dự án:** DX-Asset: Open-Source Digital Asset Lifecycle Management Platform  
**Tác giả:** Nguyễn Phạm Đại Phúc (Trường Đại học Thủ Dầu Một)  
**Ngày nghiệm thu:** 25/09/2026  
**Trạng thái Phase 16J:** `COMPLETE`

---

## 1. ARCHITECTURE FINAL STATE (TRẠNG THÁI KIẾN TRÚC CUỐI CÙNG)

Qua 10 giai đoạn triển khai (Phases 16A–16J), mô hình xác thực và phân quyền của hệ thống DX-Asset đã được định hình và hoàn thiện theo đúng các nguyên tắc thiết kế:

1. **Authentication (Xác thực Identity)**:
   - Đảm nhiệm 100% bởi **Keycloak OIDC Provider** (Identity Provider).
   - Áp dụng chuẩn bảo mật **Authorization Code Flow với PKCE (S256)** trên Next.js Frontend.
   - Quản lý tài khoản, đăng nhập, đăng ký tự do (Self-registration), SSO session, làm mới token (Refresh Token), và đăng xuất (Logout) tại Keycloak Server.

2. **Authorization (Phân quyền Nghiệp vụ)**:
   - **PostgreSQL DX-Asset (`users.role`) là Source of Truth duy nhất** cho vai trò nghiệp vụ (`ADMIN`, `IT_ASSET_MANAGER`, `MANAGER`, `EMPLOYEE`).
   - Mọi claim `role` trong JWT của Keycloak hay payload từ client gửi lên đều **bị bỏ qua server-side**.
   - Backend FastAPI kiểm tra trực tiếp vai trò của người dùng từ cơ sở dữ liệu PostgreSQL thông qua dependency `get_current_user`.

3. **System Owner & Single Admin Invariant**:
   - Duy nhất tài khoản **`2424801030008@student.tdmu.edu.vn`** (Nguyễn Phạm Đại Phúc) giữ vai trò `ADMIN` trong toàn bộ hệ thống (`COUNT(role='ADMIN') == 1`).
   - Mọi nỗ lực gán vai trò `ADMIN` cho bất kỳ tài khoản khác hoặc hạ cấp (demote), vô hiệu hóa, xóa System Owner đều bị chặn lập tức từ server với lỗi `HTTP 403 Forbidden`.

---

## 2. INFRASTRUCTURE VERIFICATION (XÁC MINH HẠ TẦNG DOCKER & DB SEPARATION)

- **Keycloak Container**:
  - Image: `quay.io/keycloak/keycloak:24.0.5`
  - Mode: `start-dev --import-realm`
  - Ports: `8080:8080`
- **Tách biệt Cơ sở dữ liệu (Database Separation)**:
  - Container PostgreSQL khởi tạo 2 cơ sở dữ liệu độc lập:
    1. `dx_asset_db`: Chứa toàn bộ dữ liệu nghiệp vụ DX-Asset (`users`, `assets`, `incidents`, `maintenances`, `process_cases`,...).
    2. `keycloak_db`: Cơ sở dữ liệu riêng dành cho Keycloak IdP.
  - Keycloak tuyệt đối không dùng chung hay ghi đè vào bảng nghiệp vụ của DX-Asset.
- **Cấu hình Keycloak Realm & Client**:
  - Realm Name: `dx-asset`
  - Public Client ID: `dx-asset-frontend`
  - PKCE Code Challenge Method: `S256`
  - OIDC Discovery Endpoint: `http://localhost:8080/realms/dx-asset/.well-known/openid-configuration` (`200 OK`)
  - JWKS Endpoint: `http://localhost:8080/realms/dx-asset/protocol/openid-connect/certs` (`200 OK`, Algorithm `RS256`).

---

## 3. REAL LOGIN FLOW (LUỒNG ĐĂNG NHẬP THỰC TẾ)

- **Giao diện Đăng nhập (`/login`)**:
  - Người dùng bấm nút **"Đăng nhập bằng Keycloak SSO (OIDC)"**.
  - Client khởi tạo cặp `code_verifier` (PKCE S256) và `state` (chống CSRF) lưu trong `sessionStorage`, sau đó redirect tới Keycloak Auth Endpoint.
- **Xác thực tại Keycloak**:
  - Sau khi đăng nhập thành công trên Keycloak, Keycloak redirect về Callback Route `/auth/callback?code=...&state=...`.
- **Đổi Token & Gọi API Profile**:
  - Callback Route trao đổi `code` và `code_verifier` lấy Access Token (RS256 JWT) và Refresh Token từ Keycloak Token Endpoint.
  - Token được lưu vào `localStorage`, sau đó frontend gọi `GET /api/v1/auth/me` kèm header `Authorization: Bearer <token>`.
  - Backend FastAPI giải mã token bằng Keycloak JWKS Public Key (RS256), thực hiện identity lookup/linking, và trả về `UserResponse` cùng vai trò local từ PostgreSQL.
  - Người dùng được chuyển hướng vào trang `/dashboard`.

---

## 4. REGISTRATION & JIT PROVISIONING TEST (ĐĂNG KÝ MỚI & CẤP PHÁT TỰ ĐỘNG)

- **Self-Registration Flow**:
  - Người dùng bấm nút **"Đăng ký Tài khoản Mới (Self-Registration)"** trên trang Login.
  - Người dùng nhập thông tin đăng ký trên giao diện native của Keycloak (`prompt=create`).
- **JIT Provisioning Server-Side**:
  - Khi người dùng mới đăng nhập lần đầu tiên vào DX-Asset, backend `deps.py` nhận diện claim `sub` (UUID Keycloak) chưa tồn tại trong cơ sở dữ liệu local `users`.
  - Backend tự động tạo bản ghi `User` mới trong PostgreSQL với:
    - `keycloak_user_id = sub`
    - `email = jwt_email`
    - `role = UserRole.EMPLOYEE` *(Vai trò mặc định an toàn cho mọi tài khoản tự đăng ký)*
    - `password_hash = "EXTERNAL_KEYCLOAK_AUTHENTICATED"`
    - `is_active = True`
  - **Kết quả**: Tài khoản mới được cấp vai trò `EMPLOYEE`, không bao giờ được cấp `ADMIN`.

---

## 5. EXISTING USER LINKING (LIÊN KẾT TÀI KHOẢN ĐÃ TỒN TẠI)

- **Kịch bản**:
  - Tài khoản người dùng đã có sẵn trong local DB từ trước (như tài khoản demo hoặc nhập liệu cũ) nhưng chưa có `keycloak_user_id` (`keycloak_user_id = NULL`).
- **Cơ chế Identity Linking**:
  - Khi người dùng đăng nhập thành công bằng email tương ứng qua Keycloak, backend tra cứu theo `email`.
  - Backend tự động liên kết `keycloak_user_id = sub` vào bản ghi `users` local hiện tại.
  - **Bảo toàn Dữ liệu**: Giữ nguyên `id` (Integer) nội bộ, giữ nguyên `role` hiện tại, và giữ nguyên 100% lịch sử cấp phát, sự cố, Process Mining. Không tạo bản ghi User trùng lặp.

---

## 6. SYSTEM OWNER PROTECTION (BẢO VỆ CHỦ SỞ HỮU HỆ THỐNG)

- **System Owner Account**: `2424801030008@student.tdmu.edu.vn`
- **Xác minh Bảo vệ tại Backend & Frontend**:
  - Đăng nhập với tài khoản System Owner, nhận ngay vai trò `ADMIN`.
  - Thanh điều hướng hiển thị mục **"Quản lý người dùng"** (`/users`).
  - Trên trang `/users`, dòng tài khoản System Owner hiển thị huy hiệu cố định **`SYSTEM OWNER (ADMIN)`** kèm biểu tượng khóa.
  - Ẩn toàn bộ nút điều khiển / dropdown sửa vai trò đối với System Owner.
  - Gửi request `PATCH /api/v1/users/{owner_id}/role` qua Postman/cURL bị hệ thống từ chối lập tức với HTTP **403 Forbidden**.

---

## 7. NORMAL USER RBAC (KIỂM SOÁT PHÂN QUYỀN NGƯỜI DÙNG THƯỜNG)

- **Vai trò `EMPLOYEE`, `MANAGER`, `IT_ASSET_MANAGER`**:
  - Khi truy cập URL `/users`, component `<ProtectedRoute allowedRoles={['ADMIN']}>` từ chối truy cập và hiển thị màn hình **403 Access Denied**.
  - Nếu cố tình gọi API `GET /api/v1/users` hoặc `PATCH /api/v1/users/{id}/role`, backend `RoleChecker` chặn với HTTP **403 Forbidden**.
  - Các business API khác (`/assets`, `/assignments`, `/incidents`, `/maintenances`, `/process-mining`) hoạt động đúng theo Ma trận RBAC quy định.

---

## 8. ROLE UPDATE VERIFICATION (XÁC MINH CẬP NHẬT VAI TRÒ)

- Admin (System Owner) thực hiện đổi vai trò người dùng thông thường trên trang `/users`:
  - `EMPLOYEE` ↔ `MANAGER` ↔ `IT_ASSET_MANAGER`.
- **Kết quả Kiểm thử**:
  - Request `PATCH /api/v1/users/{user_id}/role` trả về status **200 OK**.
  - Mọi thao tác thay đổi vai trò được ghi lại vào hệ thống nhật ký kiểm toán (`ROLE_CHANGE_AUDIT`).
  - Giao diện cập nhật ngay lập tức vai trò mới. Khi refresh trang hoặc khi người dùng đăng nhập lại lần sau, vai trò mới lưu trong PostgreSQL tiếp tục được áp dụng chính xác.

---

## 9. ADMIN PRIVILEGE ESCALATION PREVENTION (CHỐNG LEO THANG QUYỀN ADMIN)

- **Thử nghiệm 1 (PATCH role = ADMIN)**:
  - Gửi request `PATCH /api/v1/users/{user_id}/role` với body `{"role": "ADMIN"}`.
  - **Kết quả**: Backend trả về **403 Forbidden** với thông điệp *"Không được phép gán vai trò ADMIN. Hệ thống chỉ cho phép duy nhất một System Owner ADMIN."*
- **Thử nghiệm 2 (Fake JWT Claim / Keycloak Realm Role)**:
  - Tạo token giả lập claim `role: "ADMIN"` hoặc gán Realm Role `ADMIN` trên Keycloak.
  - **Kết quả**: Backend đọc `User.role` trực tiếp từ PostgreSQL (`EMPLOYEE`). Client hoàn toàn bị chặn khỏi các quyền Admin.

---

## 10. TOKEN EXPIRATION & SILENT REFRESH (LÀM MỚI TOKEN TỰ ĐỘNG & ĐỒNG THỜI)

- **Cơ chế Silent Refresh Proactive & Reactive**:
  - File [api.ts](file:///d:/web/dx-asset/frontend/src/lib/api.ts): Kiểm tra thời gian hết hạn (`exp`) trước khi gửi request. Nếu token chuẩn bị hết hạn (offset 10s), tự động gọi `refreshAccessToken()`.
  - Nếu API backend trả về **401 Unauthorized**, interceptor tự động làm mới token bằng `refresh_token` qua OIDC token endpoint và retry request tối đa 1 lần.
- **Concurrency Locking (Chống Race Condition)**:
  - File [oidc.ts](file:///d:/web/dx-asset/frontend/src/lib/oidc.ts): Sử dụng biến khóa đơn in-flight `refreshPromise`. Nếu có nhiều request đồng thời khi token hết hạn, chỉ có 1 request OIDC refresh token được gửi đi; các request còn lại chờ promise này hoàn thành để dùng chung Access Token mới.

---

## 11. LOGOUT FLOW (LUỒNG ĐĂNG XUẤT TOÀN DIỆN)

- **Thao tác Logout**:
  - Người dùng bấm nút **"Đăng xuất"** trên Navbar.
  - Frontend thực hiện xóa sạch `dx_asset_access_token` và `dx_asset_refresh_token` khỏi `localStorage`.
  - Xóa trạng thái `user` trong React Context.
  - Chuyển hướng người dùng tới Keycloak End Session Endpoint (`logoutKeycloak()`).
- **Kết quả**:
  - Keycloak SSO Session bị vô hiệu hóa hoàn toàn trên Keycloak Server.
  - Trình duyệt chuyển hướng về `/login`.
  - Mọi nỗ lực truy cập protected routes hoặc gọi API protected đều bị chặn.

---

## 12. DISABLED ACCOUNT BEHAVIOR (TÀI KHOẢN BỊ VÔ HIỆU HÓA)

- Khi bản ghi `User` trong PostgreSQL có `is_active = False`:
  - Dependency `get_current_user` tại backend kiểm tra cờ `is_active`.
  - Trả về HTTP **401 Unauthorized** với thông điệp *"User account is inactive"*.
- **Giới hạn đã ghi nhận**:
  - DX-Asset không thực hiện back-channel token revocation realtime với Keycloak cho từng request (tránh overhead mạng). Access token Keycloak cũ (nếu chưa hết hạn) sẽ bị vô hiệu hóa hoàn toàn ở tầng backend DX-Asset do cờ `is_active = False` trong PostgreSQL.

---

## 13. SECURITY REGRESSION CHECKLIST (KIỂM TRA AN TOÀN BẢO MẬT)

- [x] Chữ ký JWT mã hóa bất đối xứng RS256 verify bằng Keycloak JWKS Endpoint.
- [x] Issuer `iss` được kiểm tra chuẩn hóa trailing slash với `KEYCLOAK_ISSUER_URL`.
- [x] Authorized Party `azp` / Audience `aud` được kiểm tra với `KEYCLOAK_CLIENT_ID`.
- [x] Token hết hạn hoặc có chữ ký giả mạo bị từ chối lập tức (401).
- [x] Bỏ qua claim role trong JWT, dùng 100% `users.role` từ PostgreSQL.
- [x] Chặn tuyệt đối việc gán vai trò `ADMIN` cho bất kỳ tài khoản nào khác (403).
- [x] Chặn tuyệt đối việc hạ vai trò, vô hiệu hóa, hay xóa System Owner (403).
- [x] Không ghi log hoặc xuất Access Token / Refresh Token / Client Secret ra file report hoặc console log.

---

## 14. BUSINESS REGRESSION VERIFICATION (KIỂM TRA KHÔNG PHÁ VỠ NGHIỆP VỤ)

Tất cả các phân hệ nghiệp vụ chính của nền tảng DX-Asset đã được xác minh hoạt động hoàn toàn bình thường sau khi chuyển đổi authentication:

- **Dashboard**: Thống kê tổng quan tài sản, trạng thái, sự cố và biểu đồ hoạt động.
- **Assets**: Xem danh sách, chi tiết tài sản, lọc theo phòng ban/trạng thái.
- **Assignments**: Bàn giao, thu hồi và theo dõi lịch sử cấp phát.
- **Incidents**: Báo sự cố, phân công cán bộ IT, cập nhật tiến độ xử lý.
- **Maintenance**: Quản lý lịch bảo trì, chi phí sửa chữa.
- **Smart Routing & AI Assistant**: Gợi ý kỹ thuật viên và trợ lý AI thông minh.
- **Asset Intelligence & Optimization**: Trí tuệ tài sản và mô phỏng tối ưu chi phí.
- **Process Mining**: Phân tích quy trình vết sự kiện (34 events, 18 cases) nguyên vẹn.
- **User Management & RBAC**: Quản lý người dùng dành riêng cho Admin.

---

## 15. DATABASE INTEGRITY REPORT (KẾT QUẢ VẸN TOÀN CƠ SỞ DỮ LIỆU)

Đã kiểm tra số lượng bản ghi thực tế trong cơ sở dữ liệu PostgreSQL tại thời điểm nghiệm thu Phase 16J:

| Cơ sở Dữ liệu / Bảng | Số lượng Bản ghi | Trạng thái Vẹn toàn |
| :--- | :---: | :---: |
| `users` (Tổng số người dùng) | **11** | **Vẹn toàn 100%** |
| `users.role = ADMIN` | **1** | **System Owner Invariant duy nhất (ID 7)** |
| System Owner Email | `2424801030008@student.tdmu.edu.vn` | **Chính xác System Owner** |
| `assets` | 1856 | **Vẹn toàn** |
| `asset_assignments` | 318 | **Vẹn toàn (Lịch sử nguyên vẹn)** |
| `incidents` | 12 | **Vẹn toàn** |
| `maintenances` | 10 | **Vẹn toàn** |
| `asset_histories` | 1540 | **Vẹn toàn (Audit log nguyên vẹn)** |
| `process_cases` | 18 | **Vẹn toàn Process Mining** |
| `process_events` | 34 | **Vẹn toàn Chuỗi sự kiện** |
| `technician_skills` | 13 | **Vẹn toàn Kỹ năng Kỹ thuật viên** |

- **Kết luận**: Zero data loss, không bị trùng lặp user, không bị đứt gãy khóa ngoại (Foreign Keys).

---

## 16. ALEMBIC MIGRATION STATUS

```bash
.\.venv\Scripts\alembic.exe current
.\.venv\Scripts\alembic.exe heads
```
**Kết quả**:
- Current Head: `005_add_keycloak_user_id (head)`
- Target Head: `005_add_keycloak_user_id (head)`
- **Không có migration pending, không sửa các migration 001–005 cũ**.

---

## 17. SUITE KIỂM THỬ TỰ ĐỘNG (AUTOMATED TESTS)

### 17.1 Backend Pytest Suite
```bash
backend\.venv\Scripts\pytest.exe
```
**Kết quả**: **190 / 190 tests PASSED (100% Success in 45.84s)**.

### 17.2 Frontend TypeScript Check
```bash
npx tsc --noEmit
```
**Kết quả**: **0 errors**.

### 17.3 Frontend Production Build
```bash
npm run build
```
**Kết quả**: **16 / 16 static & dynamic pages compiled successfully**.

---

## 18. GIT & DIFF AUDIT (AUDIT KHO MÃ NGUỒN)

- **`git status`**: Mã nguồn sạch, không chứa file tạm hay file debug không mong muốn.
- **`git diff --check`**: **0 whitespace errors**.
- **Secret & Token Audit**: Đã rà soát toàn bộ diff, khẳng định **không chứa bất kỳ API Key, Password, Access Token hay Refresh Token nào trong mã nguồn và báo cáo**.
- **Git State**: Không thực hiện `git commit` hay `git push` theo đúng quy tắc dừng của dự án.

---

## 19. KNOWN LIMITATIONS (CÁC GIỚI HẠN ĐÃ BIẾT)

1. **Test Harness Compatibility Endpoint**: Endpoint `POST /api/v1/auth/login` tiếp tục được giữ lại ở trạng thái Deprecated để chạy bộ unit test Pytest độc lập nhanh chóng trên CI/CD mà không cần bắt buộc khởi động container Keycloak thật.
2. **Back-channel Revocation**: Khi tài khoản bị vô hiệu hóa (`is_active = False`) trong PostgreSQL, backend DX-Asset sẽ từ chối truy cập lập tức (401), tuy nhiên Keycloak SSO session trên Keycloak IdP vẫn tồn tại cho tới khi token hết hạn tự nhiên hoặc người dùng chủ động logout.

---

## 20. FINAL VERDICT (KẾT LUẬN NGHIỆM THU)

Toàn bộ các yêu cầu của **Phase 16J — Final Keycloak Integration & Release Verification** đã được thực thi, kiểm thử tự động, và kiểm tra vẹn toàn cơ sở dữ liệu thành công 100%. Nền tảng **DX-Asset** đã hoàn tất việc nâng cấp hệ thống xác thực Keycloak OIDC an toàn, chuẩn hóa và sẵn sàng cho công bố release.

```text
PHASE 16J STATUS: COMPLETE
```
