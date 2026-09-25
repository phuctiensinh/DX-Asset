# BÁO CÁO TÍCH HỢP FASTAPI KEYCLOAK OIDC AUTHENTICATION (PHASE 16C)

**Dự án:** DX-Asset: Open-Source Digital Asset Lifecycle Management Platform  
**Tác giả:** Nguyễn Phạm Đại Phúc (Trường Đại học Thủ Dầu Một)  
**Ngày thực hiện:** 25/09/2026  
**Trạng thái Phase 16C:** `COMPLETE`

---

## 1. KIẾN TRÚC XÁC THỰC BEFORE / AFTER

```text
[TRƯỚC MIGRATION (Phase 16B)]
Frontend / Request ──> POST /auth/login (Email+Password) ──> FastAPI (Bcrypt check) ──> Internal HS256 JWT Token

[SAU MIGRATION (Phase 16C)]
Frontend / Client ──> Keycloak OIDC Token Endpoint ──> RS256 Bearer Token
                           │
                           ▼
              FastAPI Bearer Header
                           │
                           ▼
          PyJWKClient (Keycloak JWKS Cache) ──> Verify Signature, Issuer, Exp, AZP
                           │
                           ▼
            Extract Claims (sub, email, name)
                           │
                           ▼
           PostgreSQL User Lookup / JIT Provisioning (Default Role: EMPLOYEE)
                           │
                           ▼
          PostgreSQL `users.role` (Source of Truth) ──> Existing `require_roles` RBAC
```

---

## 2. JWT CLAIMS THỰC TẾ & QUYẾT ĐỊNH XÁC THỰC

### 2.1 Payload Claims thực tế từ Keycloak Token
- `iss`: `"http://localhost:8080/realms/dx-asset"`
- `sub`: `"bd889d67-19bf-4c1c-8b61-a4516fc46218"` (Keycloak User UUID)
- `azp`: `"dx-asset-frontend"` (Authorized Party / OIDC Client ID)
- `exp`: Timestamp hết hạn
- `email`: `"testuser@student.tdmu.edu.vn"`
- `preferred_username`: `"testuser"`
- `name`: `"Test User"`

### 2.2 Quyết định Xác thực Issuer & Audience (AZP)
- **Issuer Verification**: Ép buộc `iss == settings.KEYCLOAK_ISSUER_URL`.
- **AZP Verification**: Đối với Public Browser Clients, Keycloak gán `azp` thay cho `aud`. FastAPI kiểm tra `azp == settings.KEYCLOAK_CLIENT_ID`. Token có `azp` không khớp sẽ bị từ chối với HTTP 401.

---

## 3. THIẾT KẾ XÁC THỰC VÀ CACHE JWKS (`security.py`)

Thêm hàm `get_jwks_client()` và nâng cấp `decode_access_token()` trong [backend/app/core/security.py](file:///D:/web/dx-asset/backend/app/core/security.py):
- **PyJWKClient Cache Strategy**: Khóa public key được cache tự động (`cache_keys=True`, `max_cached_keys=16`, `cache_jwk_set=True`).
- **Key Rotation Support**: Khi gặp token có `kid` chưa có trong cache, `PyJWKClient` tự động làm mới JWKS endpoint từ Keycloak để lấy khóa chữ ký mới nhất.
- **Dual-Mode Compatibility**:
  - Khi token header có `alg == "RS256"`, xác thực chữ ký bất đối xứng bằng Keycloak JWKS.
  - Khi token header có `alg == "HS256"`, giải mã bằng `SECRET_KEY` nội bộ (đảm bảo tính tương thích ngược tuyệt đối với các unit test cũ).

---

## 4. DỒNG BỘ NGƯỜI DÙNG & JIT PROVISIONING (`deps.py`)

Nâng cấp dependency `get_current_user` trong [backend/app/api/deps.py](file:///D:/web/dx-asset/backend/app/api/deps.py):
1. Giải mã token RS256 hợp lệ.
2. Tra cứu local user trong PostgreSQL theo `email` hoặc `preferred_username`.
3. **Just-In-Time (JIT) Provisioning**: Nếu người dùng chưa tồn tại trong local DB (người dùng mới đăng ký tự do qua Keycloak), tự động tạo bản ghi mới với:
   - `email`: Lấy từ Keycloak Token
   - `password_hash`: `"EXTERNAL_KEYCLOAK_AUTHENTICATED"`
   - `full_name`: Lấy từ claim `name` hoặc `preferred_username`
   - `role`: `UserRole.EMPLOYEE` *(Vai trò mặc định an toàn)*
   - `is_active`: `True`

---

## 5. CƠ CHẾ ROLE SOURCE OF TRUTH & BẢO VỆ SYSTEM OWNER

1. **Role Source of Truth**:
   - Vai trò để phân quyền (Authorization) **LUÔN LUÔN LÀ `users.role`** trong PostgreSQL local.
   - Các claim gửi kèm trong JWT hay request body/query parameter hoàn toàn không thể vượt qua tầng kiểm tra của `require_roles`.
2. **System Owner Invariant**:
   - Đảm bảo duy nhất tài khoản `2424801030008@student.tdmu.edu.vn` giữ vai trò `ADMIN`.
   - JIT Provisioning chỉ cấp vai trò `EMPLOYEE` cho tài khoản mới.

---

## 6. KẾT QUẢ KIỂM THỬ BẢO MẬT & INTEGRATION TEST (`test_keycloak_auth.py`)

Bộ test suite mới trong [backend/tests/test_keycloak_auth.py](file:///D:/web/dx-asset/backend/tests/test_keycloak_auth.py) đạt **7/7 PASSED 100%**:

1. `test_real_keycloak_token_integration`: Đăng nhập lấy token thật từ Keycloak container `http://localhost:8080`, gửi Bearer token tới `/auth/me` ➔ `HTTP 200 OK`, tự động JIT Create local user với `role = EMPLOYEE`.
2. `test_keycloak_role_source_of_truth_prevents_privilege_escalation`: Tài khoản `testuser` (role `EMPLOYEE`) thử gọi endpoint yêu cầu `ADMIN` / `IT_ASSET_MANAGER` (`/api/v1/users/technicians/skills`) ➔ `HTTP 403 Forbidden`. Thử gửi body `{"role": "ADMIN"}` ➔ Vẫn bị `HTTP 403 Forbidden`.
3. `test_keycloak_tampered_jwt_signature_rejected`: Sửa đổi chữ ký JWT (Fake JWT) ➔ `HTTP 401 Unauthorized`.
4. `test_keycloak_missing_bearer_token_rejected`: Thiếu Authorization header ➔ `HTTP 401 Unauthorized`.
5. `test_keycloak_malformed_token_rejected`: Token sai định dạng JWT ➔ `HTTP 401 Unauthorized`.
6. `test_keycloak_wrong_issuer_rejected`: Token từ sai Issuer (`http://evil-hacker.com/realms/fake`) ➔ `HTTP 401 Unauthorized`.
7. `test_keycloak_expired_token_rejected`: Token hết hạn ➔ `HTTP 401 Unauthorized`.

---

## 7. KẾT QUẢ CHẠY BỘ TEST SUITE TOÀN BỘ (FULL TEST SUITE)

- **Tổng số test cases**: **172 passed / 172 items (100% PASS)**.
- Không có bất kỳ test cũ nào bị hỏng hay nảy sinh regression lỗi.

---

## 8. DANH SÁCH FILE THAY ĐỔI VÀ KHÔNG THAY ĐỔI

### 8.1 File đã thay đổi / tạo mới:
1. `backend/app/core/config.py`: Bổ sung tham số Keycloak OIDC Settings.
2. `backend/app/core/security.py`: Tích hợp PyJWKClient RS256 JWKS verification và cache.
3. `backend/app/api/deps.py`: Cập nhật `get_current_user` với Keycloak user lookup và JIT provisioning.
4. `backend/tests/test_keycloak_auth.py`: Thêm 7 unit & integration tests cho Keycloak.
5. `docs/PHASE-16C-KEYCLOAK-FASTAPI-AUTH.md`: File báo cáo Phase 16C.

### 8.2 File cố ý KHÔNG thay đổi:
- Giao diện Next.js Frontend.
- Database Schema / Alembic Migrations (Phase 16D sẽ thực hiện).
- Các routers nghiệp vụ (`assets.py`, `incidents.py`, `maintenances.py`, `intelligence.py`, `optimization.py`, `process_mining.py`).

---

## 9. KHUYẾT ĐIỂM HẠN CHẾ & YÊU CẦU PHASE TIẾP THEO

- **Hạn chế**: Hiện tại local `users` mới chỉ được map qua `email`. Cần thêm cột `keycloak_user_id` vào bảng `users` ở DB để liên kết trực tiếp UUID từ Keycloak.
- **Yêu cầu Phase 16D**: Tạo Alembic DB Migration bổ sung cột `keycloak_user_id` (`String(255)`, `Unique`, `Nullable`, `Index`) vào bảng `users`.

---

## 10. ACCEPTANCE CRITERIA CHECKLIST

- [x] FastAPI xác minh được Keycloak Access Token RS256
- [x] Chữ ký RS256 được verify bằng Keycloak JWKS
- [x] Keycloak JWKS public keys được cache tự động
- [x] Chiến lược Key Rotation tự động cập nhật khi gặp `kid` mới
- [x] Issuer được kiểm tra chính xác với `KEYCLOAK_ISSUER_URL`
- [x] Expiration được kiểm tra chính xác
- [x] Audience / AZP được xử lý chuẩn xác
- [x] Identity được trích xuất từ Token đã xác thực
- [x] Local DX-Asset `users` được mapping chuẩn xác
- [x] PostgreSQL `users.role` là Source of Truth duy nhất cho Authorization
- [x] Helper `require_roles` và `RoleChecker` hoạt động hoàn hảo
- [x] Invariant System Owner ADMIN duy nhất được bảo vệ
- [x] Fake role / Privilege escalation bị ngăn chặn tuyệt đối (HTTP 403)
- [x] Fake JWT signature bị từ chối (HTTP 401)
- [x] Expired token bị từ chối (HTTP 401)
- [x] Wrong issuer bị từ chối (HTTP 401)
- [x] JIT provisioning tạo người dùng mới với vai trò mặc định `EMPLOYEE`
- [x] Integration test với Keycloak container thật đạt PASSED 100%
- [x] Toàn bộ 172 backend unit tests đạt PASSED 100%
- [x] Cơ sở dữ liệu nghiệp vụ nguyên vẹn và an toàn
- [x] Không ảnh hưởng tới frontend hiện tại
- [x] Không commit hoặc push code

---

```text
PHASE 16C STATUS: COMPLETE
```
