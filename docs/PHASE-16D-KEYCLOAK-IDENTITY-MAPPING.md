# BÁO CÁO THIẾT KẾ DỒNG BỘ ĐỊNH DANH CƠ SỞ DỮ LIỆU VÀ JIT PROVISIONING (PHASE 16D)

**Dự án:** DX-Asset: Open-Source Digital Asset Lifecycle Management Platform  
**Tác giả:** Nguyễn Phạm Đại Phúc (Trường Đại học Thủ Dầu Một)  
**Ngày thực hiện:** 25/09/2026  
**Trạng thái Phase 16D:** `COMPLETE`

---

## 1. ALEMBIC MIGRATION & SCHEMA CHANGE

### 1.1 Chi tiết Alembic Migration 005
- **File Migration**: [backend/alembic/versions/005_add_keycloak_user_id.py](file:///D:/web/dx-asset/backend/alembic/versions/005_add_keycloak_user_id.py)
- **Revision ID**: `005_add_keycloak_user_id`
- **Revises**: `004_add_process_event_log`
- **Không thay đổi các Migration cũ**: Giữ nguyên `001_initial_schema.py`, `002_add_maintenance_table.py`, `003_add_smart_routing_and_skills.py`, `004_add_process_event_log.py`.

### 1.2 Thay đổi Cấu trúc Bảng `users`
- **Tên cột mới**: `keycloak_user_id`
- **Kiểu dữ liệu**: `String(255)` / `VARCHAR(255)`
- **Thuộc tính**:
  - `nullable = True` (Đảm bảo an toàn trong giai đoạn chuyển tiếp migration).
  - `unique = True` (Constraint `uq_users_keycloak_user_id` chặn tuyệt đối việc trùng lặp Keycloak UUID).
  - `index = True` (Index `ix_users_keycloak_user_id` tối ưu tốc độ tra cứu người dùng mỗi request).

### 1.3 Kết quả Kiểm thử Migration & Rollback
1. **Lệnh Upgrade**: `.venv\Scripts\python -m alembic upgrade head` ➔ Thành công.
2. **Kiểm tra State**: `alembic current` và `alembic heads` đồng nhất tại `005_add_keycloak_user_id (head)`.
3. **Kiểm thử Rollback**: `.venv\Scripts\python -m alembic downgrade -1` (về 004) sau đó `upgrade head` (lên 005) ➔ Hoạt động mượt mà 100%, không bị mất mát hay rò rỉ dữ liệu.

---

## 2. QUY TRÌNH DỒNG BỘ ĐỊNH DANH & FIRST-TIME LINKING (JIT FLOW)

Luồng xử lý tại hàm `get_current_user` trong [backend/app/api/deps.py](file:///D:/web/dx-asset/backend/app/api/deps.py#L38-L77):

```text
Incoming Bearer Token (Verified RS256)
               │
               ▼ 1. Tra cứu Ưu tiên (Indexed Lookup)
db.query(User).filter(User.keycloak_user_id == sub)
               │
      ┌────────┴────────┐
   TÌM THẤY          KHÔNG THẤY
      │                 │
      ▼                 ▼ 2. Tra cứu Lần Đăng nhập Đầu tiên (First-time Linking)
Sử dụng User local  db.query(User).filter(User.email == token_email)
(Role local giữ nguyên)   │
                ┌───────┴───────┐
             TÌM THẤY         KHÔNG THẤY
                │                │
                ▼                ▼ 3. JIT Provisioning Người dùng Mới
     Check Conflict Identity     Tạo local User:
     - Nếu sub đã link: OK       - keycloak_user_id = sub
     - Nếu NULL: Update sub      - email = token_email
       và Commit                 - role = UserRole.EMPLOYEE (Default)
     - Nếu sub khác: 401 Error   - Transaction Commit
```

---

## 3. XỬ LÝ CONFLICT NGUYÊN TẮC VÀ DỊCH VỤ CONCURRENCY

### 3.1 Chống Giả mạo / Tráo đổi Định danh (Identity Conflict Prevention)
Nếu một token mang Keycloak `sub = A` cố gắng đăng nhập dưới email `user@example.com` nhưng tài khoản này đã được liên kết với `keycloak_user_id = B` trước đó:
- Backend phát hiện `existing_user.keycloak_user_id != sub`.
- Lập tức hủy giao dịch, ghi log cảnh báo an ninh và từ chối request với `HTTP 401 Unauthorized`.

### 3.2 An toàn Tranh chấp Concurrency (Race Condition Safety)
Nếu 2 request đồng thời từ cùng một Keycloak User mới tới Backend khi chưa có bản ghi local:
- Transaction 1 khởi tạo và `commit()`.
- Transaction 2 gặp lỗi `IntegrityError` từ database unique constraint.
- Catch `IntegrityError`, tự động `db.rollback()` và `re-query` cơ sở dữ liệu để lấy bản ghi `User` do Transaction 1 vừa tạo. Đảm bảo **tối đa duy nhất 1 bản ghi local** được khởi tạo.

---

## 4. CƠ CHẾ ROLE SOURCE OF TRUTH & ADMIN INVARIANT

1. **Role Source of Truth**:
   - Vai trò nghiệp vụ của người dùng **LUÔN LUÔN LÀ `users.role`** trong PostgreSQL local.
   - Khi thực hiện First-time Linking (liên kết `keycloak_user_id` vào tài khoản cũ như `admin@dxasset.local`), vai trò `ADMIN` hoặc `IT_ASSET_MANAGER` của tài khoản cũ **ĐƯỢC GIỮ NGUYÊN 100%**.
2. **System Owner Invariant**:
   - Tài khoản `2424801030008@student.tdmu.edu.vn` được gắn vai trò `ADMIN` ở tầng database và không bị hạ quyền qua luồng JIT.

---

## 5. KẾT QUẢ KIỂM THỬ BẮT BUỘC (JIT TEST MATRIX)

Tất cả 9 test cases trong [backend/tests/test_keycloak_auth.py](file:///D:/web/dx-asset/backend/tests/test_keycloak_auth.py) đạt **PASSED 100%**:

| Case | Tên Test Case | Mô tả & Kết quả |
| :--- | :--- | :--- |
| **Case 1** | `test_keycloak_first_time_linking_existing_user` | User cũ (`admin@dxasset.local`) chưa link sub -> Đăng nhập gán `keycloak_user_id = sub`, role giữ nguyên `ADMIN` ➔ **PASSED** |
| **Case 2** | `test_keycloak_existing_linked_user_lookup_by_sub` | User đã link -> Tra cứu trực tiếp theo `sub`, không bị duplicate, role giữ nguyên ➔ **PASSED** |
| **Case 3** | `test_real_keycloak_token_integration_and_jit_provisioning` | Token từ Keycloak thật -> JIT Create local User mới với role `EMPLOYEE` ➔ **PASSED** |
| **Case 4** | `test_keycloak_role_source_of_truth_prevents_privilege_escalation` | Giả mạo claim/request role -> Local role quyết định, chặn HTTP 403 ➔ **PASSED** |
| **Case 5** | `test_keycloak_identity_conflict_rejected` | Xung đột sub khác trên cùng email -> Hủy request HTTP 401 ➔ **PASSED** |
| **Case 6** | `test_system_owner_admin_invariant` | System Owner `2424801030008@student.tdmu.edu.vn` đăng nhập nhận role `ADMIN` ➔ **PASSED** |
| **Case 7** | `test_keycloak_tampered_jwt_signature_rejected` | Chữ ký JWT bị sửa đổi -> Từ chối HTTP 401 ➔ **PASSED** |
| **Case 8** | `test_keycloak_wrong_issuer_rejected` | Token từ issuer không hợp lệ -> Từ chối HTTP 401 ➔ **PASSED** |
| **Case 9** | `test_keycloak_expired_token_rejected` | Token hết hạn -> Từ chối HTTP 401 ➔ **PASSED** |

---

## 6. KẾT QUẢ CHẠY BỘ TEST SUITE TOÀN BỘ (FULL TEST SUITE)

- **Tổng số test cases**: **174 passed / 174 items (100% PASS)**.
- Không có bất kỳ regression lỗi nào trên các module `assets`, `assignments`, `incidents`, `maintenances`, `intelligence`, `optimization`, `process_mining`.

---

## 7. DANH SÁCH FILE THAY ĐỔI VÀ KHÔNG THAY ĐỔI

### 7.1 File đã thay đổi / tạo mới:
1. `backend/app/models/user.py`: Thêm thuộc tính `keycloak_user_id` vào ORM Model `User`.
2. `backend/app/schemas/user.py`: Thêm `keycloak_user_id` vào `UserResponse` Pydantic Schema.
3. `backend/alembic/versions/005_add_keycloak_user_id.py`: File migration Alembic 005.
4. `backend/app/api/deps.py`: Cập nhật `get_current_user` hỗ trợ `keycloak_user_id` lookup, First-time linking & Conflict handling.
5. `backend/tests/test_keycloak_auth.py`: Cập nhật bộ test cases cho Phase 16D.
6. `docs/PHASE-16D-KEYCLOAK-IDENTITY-MAPPING.md`: File báo cáo Phase 16D.

### 7.2 File cố ý KHÔNG thay đổi:
- Giao diện Next.js Frontend.
- Các migration Alembic cũ (001 đến 004).
- Các routers nghiệp vụ (`assets.py`, `incidents.py`, `maintenances.py`, `intelligence.py`, `optimization.py`, `process_mining.py`).

---

## 8. KHUYẾT ĐIỂM HẠN CHẾ & YÊU CẦU PHASE TIẾP THEO

- **Hạn chế**: Cột `keycloak_user_id` đã được bổ sung và JIT mapping ở Backend. Tuy nhiên chưa có API dành cho Admin quản lý role hoặc endpoint đồng bộ hồ sơ đăng nhập ở lần đầu.
- **Yêu cầu Phase 16E**: Xây dựng Backend User First-Login Synchronization Flow & API quản lý vai trò người dùng (User Role Management API với quy tắc bảo vệ System Owner).

---

## 9. ACCEPTANCE CRITERIA CHECKLIST

- [x] Migration 005 (`005_add_keycloak_user_id.py`) tạo và áp dụng thành công
- [x] Cột `users.keycloak_user_id` tồn tại (`VARCHAR(255)`, `nullable=True`, `unique=True`, `index=True`)
- [x] Dữ liệu bản ghi người dùng và khóa ngoại hiện có không bị ảnh hưởng
- [x] Tài khoản System Owner `2424801030008@student.tdmu.edu.vn` duy trì vai trò `ADMIN`
- [x] First-time Identity Linking hoạt động chính xác theo email lần đăng nhập đầu tiên
- [x] Linked user được tra cứu trực tiếp bằng `sub` ở các request tiếp theo
- [x] JIT provisioning tạo người dùng mới với vai trò mặc định `EMPLOYEE`
- [x] Claim role từ Token không thể đè lên vai trò `users.role` local
- [x] Xung đột sub/email được ngăn chặn và trả về HTTP 401 an toàn
- [x] Tranh chấp Concurrency được xử lý an toàn bằng rollback & re-query
- [x] Lệnh `alembic upgrade head` đạt thành công
- [x] Thử nghiệm `alembic downgrade -1` và `upgrade head` đạt 100% không mất dữ liệu
- [x] RBAC Regression test đạt PASSED
- [x] Security negative tests đạt PASSED
- [x] Toàn bộ 174 backend unit tests đạt PASSED 100%
- [x] Tính vẹn toàn cơ sở dữ liệu đạt PASS
- [x] Không commit hoặc push code

---

```text
PHASE 16D STATUS: COMPLETE
```
