# PHASE 16H — SYSTEM OWNER / SINGLE ADMIN HARDENING

## 1. MỤC TIÊU & TỔNG QUAN

Phase 16H tập trung củng cố (Hardening) tuyệt đối cơ chế **System Owner duy nhất / Single ADMIN** cho toàn bộ nền tảng DX-Asset.

Business Rule cốt lõi được thắt chặt:
- **System Owner Duy Nhất**: `2424801030008@student.tdmu.edu.vn` (Nguyễn Phạm Đại Phúc).
- Chỉ duy nhất tài khoản System Owner được phép sở hữu `role = UserRole.ADMIN` trong PostgreSQL.
- Tuyệt đối không cho phép tạo hoặc tồn tại ADMIN thứ hai dưới bất kỳ hình thức nào.
- PostgreSQL `users.role` tiếp tục là **Source of Truth duy nhất** cho phân quyền (Authorization).
- Keycloak JWT claims, Keycloak Realm/Client Roles, email domain hay dữ liệu client gửi lên KHÔNG bao giờ được dùng để tự nâng quyền thành ADMIN.

---

## 2. AUDIT CÁC ĐƯỜNG CÓ THỂ TẠO HOẶC GÁN VAI TRÒ ADMIN

Đã rà soát toàn bộ repository và xác định các điểm tiềm ẩn rủi ro trước khi gia cố:

1. **JIT Provisioning (`backend/app/api/deps.py`)**: 
   - *Trước gia cố*: Mặc định gán `role = UserRole.EMPLOYEE`, nhưng chưa có điều kiện rẽ nhánh bảo vệ System Owner khi khởi tạo tài khoản mới.
   - *Đã gia cố*: Đã cập nhật logic gán vai trò `assigned_role = UserRole.ADMIN if clean_email == SYSTEM_OWNER_EMAIL else UserRole.EMPLOYEE`. Chỉ duy nhất email System Owner mới được cấp `ADMIN` khi JIT provisioning.

2. **Cập nhật Vai trò qua API (`backend/app/api/v1/users.py`)**:
   - *Trước gia cố*: Đã có quy tắc ngăn `role == UserRole.ADMIN` đối với người dùng thường và ngăn demote System Owner.
   - *Đã gia cố*: Thắt chặt bảo vệ System Owner khỏi các thao tác hạ cấp (demote), sửa vai trò, hoặc vô hiệu hóa server-side.

3. **Dữ liệu Mẫu / Seed Data (`scripts/seed_data.py`)**:
   - *Trước gia cố*: Cấu hình cũ seed `admin@dxasset.local` làm `ADMIN` bên cạnh System Owner.
   - *Đã gia cố*: Đã cập nhật `scripts/seed_data.py` để nạp `2424801030008@student.tdmu.edu.vn` là `ADMIN` duy nhất. Tài khoản demo `admin@dxasset.local` được chuyển thành `IT_ASSET_MANAGER` (dành cho kiểm thử legacy authentication cho tới Phase 16I).

---

## 3. THỰC THI BẢO VỆ TẠI BACKEND (BACKEND ENFORCEMENT)

Backend áp dụng các quy tắc bảo mật độc lập:

- **JIT Provisioning**: Mọi tài khoản mới đăng ký qua Keycloak có email khác System Owner đều tự động nhận vai trò `EMPLOYEE`.
- **Identity Linking**: Khi người dùng đăng nhập lần đầu qua Keycloak, chỉ liên kết `keycloak_user_id = sub` dựa trên email và **bảo toàn nguyên vẹn `users.role` hiện tại** từ PostgreSQL.
- **Role Control API (`PATCH /api/v1/users/{id}/role`)**:
  - Chỉ cho phép gán vai trò: `EMPLOYEE`, `MANAGER`, `IT_ASSET_MANAGER`.
  - Mọi yêu cầu gán `role = ADMIN` đều bị chặn với HTTP **403 Forbidden**.
  - Mọi yêu cầu thay đổi vai trò của System Owner (`2424801030008@student.tdmu.edu.vn`) đều bị chặn với HTTP **403 Forbidden**.
- **Chống JWT Giả mạo & Claim Nâng quyền**:
  - Backend bỏ qua mọi claim `role` chứa trong JWT.
  - Phân quyền luôn dựa trên kết quả truy vấn bản ghi `User` thực tế từ PostgreSQL DB thông qua `get_current_user`.
- **Bảo vệ System Owner**:
  - Server-side chặn tuyệt đối việc demote, đổi role, xóa hay vô hiệu hóa System Owner.

---

## 4. AN TOÀN DỮ LIỆU & CONCURRENCY (DATABASE SAFETY)

- **Database Invariant Verification**:
  Đã kiểm tra thực tế cơ sở dữ liệu PostgreSQL qua truy vấn:
  ```sql
  SELECT id, email, role FROM users WHERE role = 'ADMIN';
  ```
  **Kết quả thực tế**:
  ```text
  [(7, '2424801030008@student.tdmu.edu.vn', 'UserRole.ADMIN')]
  ```
  - **ADMIN Count**: **Đúng 1 bản ghi duy nhất**.
  - **System Owner Email**: `2424801030008@student.tdmu.edu.vn`.
- **Concurrency & Race Condition Protection**:
  - Logic JIT Provisioning và Role Update xử lý giao dịch transactional với rollback an toàn khi có xung đột định danh hoặc cập nhật đồng thời.
  - Phân tách vai trò cấp bậc ở cấp ứng dụng kết hợp kiểm tra email System Owner loại bỏ nguy cơ hai request đồng thời tạo hai ADMIN.

---

## 5. RANH GIỚI BẢO MẬT KEYCLOAK VÀ FRONTEND

- **Keycloak Boundary**:
  - Keycloak OIDC hoàn toàn chịu trách nhiệm về Authentication (Identity, Password, PKCE Token issuance).
  - Keycloak KHÔNG quyết định Business Roles của DX-Asset.
- **Frontend UX Boundary**:
  - Trang `/users` được bảo vệ bởi `<ProtectedRoute allowedRoles={['ADMIN']}>`.
  - Dòng tài khoản System Owner hiển thị huy hiệu cố định **`SYSTEM OWNER (ADMIN)`** kèm biểu tượng khóa, ẩn toàn bộ nút điều khiển.
  - Bộ chọn vai trò cho các tài khoản khác chỉ chứa 3 lựa chọn (`EMPLOYEE`, `MANAGER`, `IT_ASSET_MANAGER`), tuyệt đối không có lựa chọn `ADMIN`.
  - Frontend chỉ đóng vai trò trải nghiệm người dùng (UX); Backend kiểm tra và bảo vệ độc lập trên server.

---

## 6. KẾT QUẢ KIỂM THỬ (TEST RESULTS)

### 6.1. Backend Pytest Suite

```bash
backend\.venv\Scripts\pytest.exe
```
**Kết quả**: **190 / 190 tests PASSED (100% Success)**

Bao gồm các test case bắt buộc của Phase 16H:
1. `test_single_admin_database_invariant`: Kiểm tra trực tiếp DB invariant, khẳng định chỉ có duy nhất 1 ADMIN mang email `2424801030008@student.tdmu.edu.vn`.
2. `test_patch_role_to_admin_forbidden`: ADMIN không thể nâng user thường thành ADMIN (403).
3. `test_patch_role_system_owner_demotion_forbidden`: ADMIN không thể hạ cấp System Owner (403).
4. `test_fake_role_claim_in_jwt`: Token giả claim role ADMIN bị từ chối truy cập (403).
5. `test_patch_role_by_non_admin_forbidden`: Người dùng không phải ADMIN không thể truy cập API đổi role (403).
6. `test_patch_role_valid_transitions`: Chuyển đổi hợp lệ giữa các vai trò `EMPLOYEE` ↔ `MANAGER` ↔ `IT_ASSET_MANAGER`.
7. `test_keycloak_first_time_linking_existing_user`: Identity linking giữ nguyên vai trò System Owner ADMIN.

### 6.2. Frontend TypeScript Check

```bash
npx tsc --noEmit
```
**Kết quả**: **0 errors**.

### 6.3. Frontend Next.js Production Build

```bash
npm run build
```
**Kết quả**: **16 / 16 static & dynamic pages compiled successfully**.

### 6.4. Alembic & Migration Status

```bash
.\.venv\Scripts\alembic.exe current
.\.venv\Scripts\alembic.exe heads
```
**Kết quả**: `005_add_keycloak_user_id (head)` — Toàn bộ cấu trúc migration đồng bộ và hợp lệ.

---

## 7. CÁC TẬP TIN ĐÃ THAY ĐỔI (FILES CHANGED)

- `backend/app/api/deps.py`: Cập nhật logic JIT provisioning đảm bảo chỉ System Owner nhận vai trò ADMIN.
- `scripts/seed_data.py`: Cập nhật dữ liệu mẫu với System Owner duy nhất giữ vai trò ADMIN và `admin@dxasset.local` giữ vai trò IT Manager.
- `backend/tests/conftest.py`: Củng cố các DB fixtures đảm bảo lấy đúng tài khoản hoạt động.
- `backend/tests/test_keycloak_auth.py`: Cập nhật test cases liên kết định danh với System Owner.
- `backend/tests/test_user_management.py`: Thêm test case kiểm tra Single Admin DB Invariant và cách ly test data.
- `docs/PHASE-16H-SINGLE-ADMIN-HARDENING.md`: Tài liệu báo cáo hoàn thành Phase 16H.

---

## 8. TRẠNG THÁI HOÀN THÀNH

```text
PHASE 16H STATUS: COMPLETE
```
