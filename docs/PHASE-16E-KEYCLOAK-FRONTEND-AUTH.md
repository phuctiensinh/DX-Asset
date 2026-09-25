# BÁO CÁO MIGRATION NEXT.JS KEYCLOAK LOGIN & REGISTRATION (PHASE 16E - COMPLETE & VERIFIED)

**Dự án:** DX-Asset: Open-Source Digital Asset Lifecycle Management Platform  
**Tác giả:** Nguyễn Phạm Đại Phúc (Trường Đại học Thủ Dầu Một)  
**Ngày cập nhật:** 25/09/2026  
**Trạng thái Phase 16E:** `COMPLETE`

---

## 1. PHÂN TÍCH NGUYÊN NHÂN GỐC RỄ BẢNG CHẨN ĐOÁN (ROOT CAUSE ANALYSIS)

Dựa trên hình ảnh DevTools Chrome console và kết quả truy vấn đối chiếu giữa PostgreSQL Database `dx_asset_db` và Keycloak Database `dx-asset`, hai nguyên nhân chính gây ra lỗi `401 Unauthorized` khi người dùng bấm **"Đăng nhập bằng Keycloak SSO (OIDC)"** đã được xác định:

### 1.1 Xung đột Identity do Chuỗi Mock Sub của Unit Test (`test_keycloak_auth.py`)
* **Hiện tượng**: Khi đăng nhập bằng tài khoản Admin/System Owner `2424801030008@student.tdmu.edu.vn` (hoặc `admin@dxasset.local`), backend trả về `401 Unauthorized` trên `GET /api/v1/auth/me`.
* **Nguyên nhân**:
  - Khi bộ test suite `pytest` chạy, hàm test `test_system_owner_admin_invariant` đã thực hiện link trực tiếp chuỗi mock `sub = "system-owner-keycloak-sub-888"` vào bản ghi `users` trong PostgreSQL.
  - Khi người dùng đăng nhập thực tế qua Keycloak UI bằng tài khoản `phuctienadmin` (`2424801030008@student.tdmu.edu.vn`), Keycloak phát hành token chứa chuỗi UUID thật `sub = "133b3382-e76b-4713-a019-1703a1c0fcdc"`.
  - Phía backend `deps.py` kiểm tra: `existing_user.keycloak_user_id` (`system-owner-keycloak-sub-888`) != `incoming sub` (`133b3382-e76b-4713-a019-1703a1c0fcdc`) ➔ Phát hiện Xung đột Identity (Identity Conflict) ➔ Bắn lỗi `401 Unauthorized`.

### 1.2 Lệch Chuỗi Issuer Trailing Slash (`/`) & Quản lý Exception
* **Nguyên nhân**:
  - Token do Keycloak cấp có thể chứa claim `iss` dạng `http://localhost:8080/realms/dx-asset` hoặc có dấu `/` ở cuối.
  - Backend `security.py` và `deps.py` so sánh strict string làm điều kiện JIT / token validation bị hỏng khi xuất hiện dấu `/`.
  - Frontend `loadCurrentUser()` gọi `/auth/me` không truyền trực tiếp token vừa đổi từ Keycloak làm phụ thuộc vào timing ghi `localStorage`.

---

## 2. NỘI DUNG NÂNG CẤP VÀ FIX TRIỆT ĐỂ

### 2.1 Cô lập Unit Test không làm Ô nhiễm Database Nghiệp vụ ([backend/tests/test_keycloak_auth.py](file:///D:/web/dx-asset/backend/tests/test_keycloak_auth.py))
- Cập nhật các test case trong `test_keycloak_auth.py` (`test_keycloak_first_time_linking_existing_user`, `test_system_owner_admin_invariant`, `test_keycloak_identity_conflict_rejected`) sử dụng khối `try...finally` để khôi phục lại `keycloak_user_id` ban đầu hoặc sử dụng tài khoản mock cách ly (`conflict_test_user@dxasset.local`).
- Đã khôi phục và liên kết chính xác Keycloak sub thật `133b3382-e76b-4713-a019-1703a1c0fcdc` cho tài khoản System Owner `2424801030008@student.tdmu.edu.vn` trong PostgreSQL.

### 2.2 Chuẩn hóa Issuer & Dynamic Token Passing ([backend/app/core/security.py](file:///D:/web/dx-asset/backend/app/core/security.py), [backend/app/api/deps.py](file:///D:/web/dx-asset/backend/app/api/deps.py), [frontend/src/lib/auth-context.tsx](file:///D:/web/dx-asset/frontend/src/lib/auth-context.tsx))
- Backend `security.py` và `deps.py` so sánh issuer sử dụng `iss.rstrip("/") == expected_iss.rstrip("/")`.
- Frontend `loadCurrentUser(tokenOverride?: string)` tiếp nhận trực tiếp fresh token tại callback route ➔ Đảm bảo request `GET /auth/me` luôn truyền đúng token vừa nhận từ Keycloak.
- Tiện ích `oidc.ts` đổi sang tham số OIDC chuẩn `prompt=create` phòng ngừa NullPointerException trên Keycloak.

---

## 3. KẾT QUẢ KIỂM THỬ XÁC MINH TOÀN DIỆN (FULL VERIFICATION)

### 3.1 Ma trận Kiểm thử Đăng nhập & Xác thực Thực tế (Test Matrix)

| Kịch bản | Tài khoản / Thao tác | Phản hồi `/auth/me` | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| **System Owner Admin** | `2424801030008@student.tdmu.edu.vn` (`phuctienadmin`) | `200 OK` | Đăng nhập thành công, nhận vai trò `ADMIN` từ PostgreSQL local | **PASS** |
| **Testuser Đã tồn tại** | `testuser@student.tdmu.edu.vn` (`testuser`) | `200 OK` | Đăng nhập thành công, nhận vai trò `EMPLOYEE` từ PostgreSQL local | **PASS** |
| **User Mới Tự Đăng ký** | Đăng ký tài khoản mới trên Keycloak UI | `200 OK` | Keycloak tạo user ➔ FastAPI JIT Provisioning tự tạo User local role `EMPLOYEE` ➔ Vào Dashboard | **PASS** |
| **Access Token Hết hạn** | Access Token hết hạn (> 5 phút) | `200 OK` | Silent Refresh bằng `refresh_token` qua OIDC, không văng login | **PASS** |
| **Invalid Token / Session Hết hạn** | Token sai / Refresh token hết hạn | `401 Unauthorized` | Chuyển trạng thái unauthenticated, chuyển hướng về `/login` | **PASS** |
| **Đăng xuất (Logout)** | Bấm nút "Đăng xuất" | `Redirect / Login` | Xóa sạch session local và Keycloak SSO session | **PASS** |

### 3.2 Kiểm thử Tự động & Build Success
- **Frontend TypeScript (`npx tsc --noEmit`)**: **PASSED 100% (0 errors)**.
- **Frontend Production Build (`npm run build`)**: **PASSED 100% (15/15 static & dynamic pages)**.
- **Backend Test Suite (`pytest`)**: **PASSED 100% (174/174 unit tests passed)**.

---

## 4. DANH SÁCH FILE THAY ĐỔI

1. `backend/tests/test_keycloak_auth.py`: Thêm khối `finally` khôi phục `keycloak_user_id`, sử dụng user cách ly cho test identity conflict.
2. `backend/app/core/security.py`: Thêm chuẩn hóa trailing-slash issuer và kiểm tra azp/aud linh hoạt.
3. `backend/app/api/deps.py`: Chuẩn hóa issuer check trong JIT, giới hạn độ dài chuỗi và xử lý exception an toàn.
4. `frontend/src/lib/auth-context.tsx`: Nâng cấp `loadCurrentUser(tokenOverride?: string)` nhận trực tiếp fresh token.
5. `frontend/src/app/auth/callback/page.tsx`: Truyền fresh token vào `loadCurrentUser`, thêm `processedRef` guard và `<Suspense>` boundary.
6. `frontend/src/lib/api.ts`: Quản lý refresh token lifecycle, proactive / reactive silent refresh.
7. `frontend/src/lib/oidc.ts`: Đổi `kc_action=register` thành tham số OIDC chuẩn `prompt=create`, thêm `refreshAccessToken()`.
8. `frontend/src/app/dashboard/page.tsx`: Fix React duplicate key warning (`key={`dept-${dept.department_id ?? 'null'}-${index}`}`).
9. `docs/PHASE-16E-KEYCLOAK-FRONTEND-AUTH.md`: Báo cáo chi tiết kết quả.

---

```text
PHASE 16E STATUS: COMPLETE
```
