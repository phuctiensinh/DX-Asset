# PHASE 16F — DX-ASSET USER MANAGEMENT & ADMIN ROLE CONTROL

## 1. MỤC TIÊU & TỔNG QUAN

Phase 16F mở rộng hệ thống xác thực Keycloak (Phase 16A-16E) bằng cách triển khai chức năng **Quản lý người dùng và Phân quyền (User Management & Role Control)** dành riêng cho vai trò **ADMIN (System Owner)**.

---

## 2. NGUỒN SỰ THẬT VỀ VAI TRÒ (ROLE SOURCE OF TRUTH)

- **Source of Truth**: Bản ghi `users.role` trong cơ sở dữ liệu **PostgreSQL** là nguồn duy nhất quyết định quyền hạn nghiệp vụ của người dùng.
- **Keycloak Realm Roles**: KHÔNG được sử dụng làm nguồn phân quyền nghiệp vụ.
- **JWT Claims**: Mọi claim `role` trong JWT (nếu có) KHÔNG được tin tưởng ở phía Backend. Backend luôn truy vấn `User` trực tiếp từ PostgreSQL thông qua `get_current_user` dependency.
- **Server-Side Authorization**: Mọi API quản lý người dùng đều kiểm tra `current_user.role == UserRole.ADMIN` trên server.

---

## 3. CHÍNH SÁCH BẢO VỆ SYSTEM OWNER & QUY TẮC CHUYỂN VAI TRÒ

### 3.1. System Owner Duy Nhất

- **System Owner Email**: `2424801030008@student.tdmu.edu.vn`
- Chỉ duy nhất tài khoản System Owner được phép giữ vai trò `ADMIN`.

### 3.2. Quy Tắc Phân Quyền & Bảo Vệ (Owner Protection Rules)

1. **Bảo vệ System Owner**:
   - KHÔNG cho phép hạ vai trò của System Owner (`ADMIN` → `EMPLOYEE`, `MANAGER`, `IT_ASSET_MANAGER`). Yêu cầu `PATCH /users/{owner_id}/role` trả về **403 Forbidden**.
   - KHÔNG cho phép xóa, vô hiệu hóa hoặc thay đổi email/keycloak_user_id của System Owner thông qua API role management.
2. **Ngăn tạo thêm ADMIN mới**:
   - Gửi yêu cầu nâng vai trò bất kỳ người dùng khác thành `ADMIN` (`PATCH /users/{user_id}/role` với `role = ADMIN`) sẽ bị chặn và trả về **403 Forbidden**.
3. **Các chuyển đổi vai trò hợp lệ (Chỉ dành cho tài khoản không phải Owner)**:
   - `EMPLOYEE` ↔ `MANAGER` ↔ `IT_ASSET_MANAGER`

---

## 4. DESIGN VÀ CÁC API ENDPOINTS

Tất cả các endpoint nằm trong router `app.api.v1.users`:

| Phương thức | Endpoint | Yêu cầu vai trò | Mô tả |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/users` | `ADMIN` | Lấy danh sách toàn bộ người dùng trong hệ thống |
| `GET` | `/api/v1/users/{user_id}` | `ADMIN` | Lấy thông tin chi tiết một người dùng theo ID |
| `PATCH` | `/api/v1/users/{user_id}/role` | `ADMIN` | Cập nhật vai trò (Role) của người dùng |
| `GET` | `/api/v1/users/technicians/skills` | `ADMIN`, `IT_ASSET_MANAGER` | Lấy danh sách kỹ thuật viên kèm điểm kỹ năng |
| `POST` | `/api/v1/users/{user_id}/skills` | `ADMIN`, `IT_ASSET_MANAGER` | Thiết lập điểm kỹ năng cho kỹ thuật viên |

### Nhật ký Kiểm toán (Audit History)

Mọi thao tác thay đổi vai trò hợp lệ đều được ghi lại vào log hệ thống dưới dạng `ROLE_CHANGE_AUDIT`:
```text
ROLE_CHANGE_AUDIT: Admin '2424801030008@student.tdmu.edu.vn' (ID 7) changed role of target user 'employee1@dxasset.local' (ID 4) from 'EMPLOYEE' to 'MANAGER'
```

---

## 5. GIAO DIỆN FRONTEND & NAVBAR

- **Thanh điều hướng (Navbar)**: Mục menu **"Quản lý người dùng"** (`/users`) CHỈ hiển thị khi người dùng có `user.role === 'ADMIN'`.
- **Trang Quản lý Người dùng (`/users`)**:
  - Được bảo vệ bởi `<ProtectedRoute allowedRoles={['ADMIN']}>`. Nếu vai trò khác truy cập trực tiếp URL, màn hình hiển thị **403 Access Denied**.
  - Hiển thị thống kê tổng quan (Tổng số người dùng, System Owner, IT Managers, Managers/Employees).
  - Bảng người dùng hiển thị: Avatar, Họ tên, Email, Phòng ban, Vai trò hiện tại, Trạng thái liên kết Keycloak SSO, Ngày khởi tạo.
  - Hiển thị Huy hiệu đặc biệt **`SYSTEM OWNER (ADMIN)`** và khóa bộ chọn vai trò đối với tài khoản `2424801030008@student.tdmu.edu.vn`.
  - Bộ chọn vai trò đối với người dùng thông thường gồm: `EMPLOYEE`, `MANAGER`, `IT_ASSET_MANAGER` (đã ẩn lựa chọn `ADMIN`).
  - Nút cập nhật kèm hiệu ứng loading và thông báo phản hồi (success/error toast).

---

## 6. KẾT QUẢ KIỂM THỬ (TEST RESULTS)

### 6.1. Backend Pytest Suite

```bash
.\.venv\Scripts\pytest.exe
```
**Kết quả**: **187 / 187 tests PASSED** (Bao gồm các test case cho anonymous 401, non-ADMIN 403, ADMIN 200, System Owner protection 403, Admin creation restriction 403, fake role claim in JWT verification 403, JIT provisioning, v.v.).

### 6.2. Frontend TypeScript & Next.js Build

```bash
npx tsc --noEmit
npm run build
```
**Kết quả**:
- TypeScript typecheck: **0 errors**.
- Next.js build: **16/16 pages compiled & generated successfully** (bao gồm route `/users`).

---

## 7. TRẠNG THÁI HOÀN THÀNH

```text
PHASE 16F STATUS: COMPLETE
```
