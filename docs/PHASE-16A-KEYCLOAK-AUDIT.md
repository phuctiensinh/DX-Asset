# BÁO CÁO AUDIT AUTHENTICATION VÀ THIẾT KẾ MIGRATION SANG KEYCLOAK (PHASE 16A)

**Dự án:** DX-Asset: Open-Source Digital Asset Lifecycle Management Platform  
**Tác giả:** Nguyễn Phạm Đại Phúc (Trường Đại học Thủ Dầu Một)  
**Ngày lập:** 25/09/2026  
**Trạng thái Phase 16A:** `READY FOR IMPLEMENTATION`

---

## 1. CURRENT AUTHENTICATION ARCHITECTURE (KIẾN TRÚC XÁC THỰC HIỆN TẠI)

Hệ thống DX-Asset hiện tại đang sử dụng cơ chế đăng nhập nội bộ dựa trên **JWT (JSON Web Token)** với phương thức mã hóa khóa đối xứng (Symmetric Encryption).

### 1.1 Chi tiết Kỹ thuật Backend Authentication
- **Thư viện JWT & Hashing**:
  - Mã hóa password: `passlib[bcrypt]` trong [backend/app/core/security.py](file:///D:/web/dx-asset/backend/app/core/security.py#L7-L15) bằng thuật toán `bcrypt`.
  - Tạo và giải mã JWT: Thư viện `PyJWT` trong [backend/app/core/security.py](file:///D:/web/dx-asset/backend/app/core/security.py#L17-L41).
- **Thuật toán & Secret Key**:
  - Thuật toán mã hóa: `HS256` (HMAC SHA-256).
  - Khóa bí mật: `SECRET_KEY` cấu hình trong [backend/app/core/config.py](file:///D:/web/dx-asset/backend/app/core/config.py#L7), lấy mặc định hoặc từ file `.env`.
  - Thời gian hết hạn Access Token: `ACCESS_TOKEN_EXPIRE_MINUTES = 480` (8 tiếng).
- **Cấu trúc JWT Payload Claims**:
  ```json
  {
    "sub": "1",
    "exp": 1790352000,
    "email": "admin@dxasset.local",
    "role": "ADMIN"
  }
  ```
  - `sub`: Chứa `id` của người dùng dưới dạng chuỗi `str(user.id)`.
  - `exp`: Thời gian hết hạn của token.
  - `email`: Email người dùng.
  - `role`: Chuỗi đại diện cho UserRole Enum (vd: `"ADMIN"`, `"EMPLOYEE"`).

### 1.2 Luồng xử lý Authentication hiện tại
1. **Endpoint `POST /api/v1/auth/login`**:
   - Tiếp nhận `email` và `password` từ client.
   - Tìm kiếm bản ghi người dùng trong bảng `users` qua `email`.
   - Kiểm tra `verify_password(request.password, user.password_hash)`.
   - Kiểm tra cờ `user.is_active`.
   - Nếu hợp lệ, sinh JWT Access Token qua `create_access_token` và trả về `TokenResponse` kèm đối tượng `UserResponse`.
2. **Endpoint `GET /api/v1/auth/me`**:
   - Nhận Bearer token qua header `Authorization: Bearer <token>`.
   - Giải mã JWT bằng `decode_access_token(token)`.
   - Trích xuất `user_id` từ `sub` claim.
   - Truy vấn SQLAlchemy `db.query(User).filter(User.id == user_id).first()`.
   - Trả về thông tin người dùng hiện tại `UserResponse`.
3. **Dependency `get_current_user`**:
   - Định nghĩa tại [backend/app/api/deps.py](file:///D:/web/dx-asset/backend/app/api/deps.py#L16-L53).
   - Sử dụng `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")`.
   - Xác thực sự tồn tại và cờ `is_active` của người dùng.

---

## 2. CURRENT USER / DATABASE ARCHITECTURE (CẤU TRÚC DATABASE NGUYÊN BẢN)

Bảng `users` giữ vai trò trung tâm trong cơ sở dữ liệu PostgreSQL của DX-Asset, vừa lưu trữ thông tin đăng nhập vừa lưu trữ các thông tin nghiệp vụ và liên kết khóa ngoại (Foreign Keys) với hầu hết các entity khác.

### 2.1 Schema Chi tiết của bảng `users`
Cấu trúc theo ORM Model [backend/app/models/user.py](file:///D:/web/dx-asset/backend/app/models/user.py#L6-L28):
- `id` (Integer, Primary Key, Auto-increment, Index): Khóa chính nội bộ.
- `email` (String(100), Unique, Not Null, Index): Email người dùng.
- `password_hash` (String(255), Not Null): Mật khẩu đã hash Bcrypt.
- `full_name` (String(100), Not Null): Họ và tên đầy đủ.
- `role` (SQLEnum UserRole, Not Null, Default `EMPLOYEE`, Index): Vai trò nghiệp vụ.
- `department_id` (Integer, FK `departments.id` ON DELETE SET NULL, Nullable, Index): Phòng ban làm việc.
- `is_active` (Boolean, Not Null, Default `True`): Trạng thái hoạt động.
- `created_at` / `updated_at` (DateTime with Timezone): Thời gian tạo và cập nhật bản ghi.

### 2.2 Các Khóa Ngoại (Foreign Keys) Trỏ tới `users.id`
`users.id` (Integer) được tham chiếu rộng rãi bởi 8 mối quan hệ chính:
1. `assets.current_user_id` -> `users.id` (ON DELETE SET NULL): Người dùng hiện đang giữ tài sản.
2. `asset_assignments.assigned_to_user_id` -> `users.id` (ON DELETE RESTRICT): Nhân viên nhận tài sản.
3. `asset_assignments.assigned_by_user_id` -> `users.id` (ON DELETE SET NULL): Cán bộ/IT thực hiện cấp phát.
4. `incidents.reporter_id` -> `users.id` (ON DELETE RESTRICT): Nhân viên báo sự cố.
5. `incidents.assigned_it_id` -> `users.id` (ON DELETE SET NULL): Kỹ thuật viên IT chịu trách nhiệm xử lý.
6. `asset_histories.performed_by_id` -> `users.id` (ON DELETE SET NULL): Người thực hiện hành động lịch sử tài sản.
7. `technician_skills.user_id` -> `users.id` (ON DELETE CASCADE): Điểm kỹ năng của kỹ thuật viên IT.
8. `process_events.user_id` -> `users.id` (ON DELETE SET NULL): Người thực hiện bước sự kiện trong Process Mining.

> **ĐÁNH GIÁ QUAN TRỌNG:**  
> Vì `users.id` (kiểu `Integer`) đang làm khóa ngoại trực tiếp ở 8 bảng nghiệp vụ khác nhau, **TUYỆT ĐỐI KHÔNG ĐƯỢC THAY ĐỔI** kiểu dữ liệu của `users.id` sang UUID hay String để khớp với Keycloak User ID.  
> Giải pháp tối ưu là giữ nguyên `users.id` làm khóa chính nội bộ, đồng thời bổ sung cột mới `keycloak_user_id` (`String(255)`, `Unique`, `Nullable`, `Index`) làm định danh ngoại liên kết tới Keycloak identity.

---

## 3. CURRENT RBAC ARCHITECTURE (MÔ HÌNH PHÂN QUYỀN HIỆN TẠI)

Hệ thống phân quyền (Role-Based Access Control) hiện tại của DX-Asset được xây dựng dựa trên Enum `UserRole` với 4 vai trò rõ ràng:

1. `ADMIN`: Quản trị viên toàn hệ thống.
2. `IT_ASSET_MANAGER`: Quản lý tài sản IT & Kỹ thuật viên xử lý sự cố / bảo trì.
3. `MANAGER`: Quản lý bộ phận, xem báo cáo, thống kê và trí tuệ tài sản.
4. `EMPLOYEE`: Nhân viên thông thường, sử dụng tài sản và gửi phản ánh sự cố.

### Cơ chế Enforce RBAC ở Backend:
- Lớp `RoleChecker` trong [backend/app/api/deps.py](file:///D:/web/dx-asset/backend/app/api/deps.py#L55-L66) kiểm tra `current_user.role in self.allowed_roles`. Trả về `HTTP 403 Forbidden` nếu vai trò người dùng không thuộc danh sách cho phép.
- Helper `require_roles(*roles)` được sử dụng làm dependency trên các route bảo vệ.

---

## 4. FRONTEND AUTH ARCHITECTURE (XÁC THỰC TRÊN FRONTEND)

Frontend sử dụng Next.js (App Router) kết hợp React Context API:

### 4.1 Quản lý Token & API Client
- File [frontend/src/lib/api.ts](file:///D:/web/dx-asset/frontend/src/lib/api.ts#L1-L36):
  - Lưu token trong `localStorage` dưới key `dx_asset_access_token`.
  - Hàm `fetchApi` tự động chèn header `Authorization: Bearer <token>` vào tất cả HTTP request.
- File [frontend/src/lib/auth-context.tsx](file:///D:/web/dx-asset/frontend/src/lib/auth-context.tsx#L27-L45):
  - Khi khởi tạo ứng dụng, `loadCurrentUser()` đọc token từ `localStorage` và gọi `GET /auth/me`.
  - Khi đăng nhập (`login`), lưu token và cập nhật trạng thái `user` trong `AuthContext`.
  - Khi đăng xuất (`logout`), xóa token khỏi `localStorage` và chuyển hướng về `/login`.

### 4.2 Điều hướng và Bảo vệ Route
- [frontend/src/components/ProtectedRoute.tsx](file:///D:/web/dx-asset/frontend/src/components/ProtectedRoute.tsx#L1-L34): Bảo vệ trang nội bộ. Nếu chưa xác thực (`!isAuthenticated`), tự động chuyển hướng về `/login`.
- [frontend/src/components/Navbar.tsx](file:///D:/web/dx-asset/frontend/src/components/Navbar.tsx#L39-L88): Ẩn/hiện các tab điều hướng (như "Trí tuệ Tài sản") dựa trên vai trò `isManagementRole` (`ADMIN`, `IT_ASSET_MANAGER`, `MANAGER`).

---

## 5. KEYCLOAK TARGET ARCHITECTURE (KIẾN TRÚC MỤC TIÊU VỚI KEYCLOAK)

Sơ đồ tổng thể luồng xác thực và phân định trách nhiệm sau khi nâng cấp:

```text
+------------------------+
|   Người dùng (User)    |
+------------------------+
            |
            v  1. Đăng nhập / Redirect
+--------------------------------------------------------+
|                 Keycloak Identity Provider              |
| - Authentication (Email/Password)                     |
| - Self-Registration & Email Verification               |
| - User Credential Management                           |
| - Issue Signed OIDC RS256 Access Token                 |
+--------------------------------------------------------+
            |
            |  2. OIDC Access Token (JWT RS256)
            v
+--------------------------------------------------------+
|                DX-Asset Frontend (Next.js)             |
| - Standard Authorization Code Flow with PKCE           |
| - Keycloak JS SDK / OIDC Client Library                |
| - Automatic Silent Token Refresh                       |
+--------------------------------------------------------+
            |
            |  3. Bearer Keycloak JWT Token
            v
+--------------------------------------------------------+
|                DX-Asset Backend (FastAPI)              |
| - Validate JWT Signature via Keycloak JWKS Endpoint    |
| - Check Issuer, Audience, Expiration                   |
| - Extract Keycloak User ID (sub)                       |
| - Synchronize / Query Local PostgreSQL User           |
| - Enforce DX-Asset Business Roles & RBAC Constraints   |
+--------------------------------------------------------+
            |
            |  4. SQL Queries (Local DX-Asset Data)
            v
+--------------------------------------------------------+
|                PostgreSQL Database                     |
| - Table `users` (id, keycloak_user_id, email, role...) |
| - Business Entities & Foreign Keys (Assets, Incidents) |
+--------------------------------------------------------+
```

---

## 6. IDENTITY MAPPING DESIGN (THIẾT KẾ ĐỒNG BỘ ĐỊNH DANH)

Để đảm bảo không phá vỡ tính vẹn toàn dữ liệu khóa ngoại và hiệu năng truy vấn, cơ chế Identity Mapping giữa Keycloak và DX-Asset PostgreSQL được thiết kế như sau:

```text
[Keycloak User Object]                         [DX-Asset PostgreSQL User Table]
- ID: "f81d4fae-7dec-11d0-a765-00a0c91e6bf6" -> keycloak_user_id (String(255), Unique, Nullable)
- email: "2424801030008@student.tdmu.edu.vn" -> email (String(100), Unique)
- name: "Nguyễn Phạm Đại Phúc"               -> full_name (String(100))
                                                id (Integer, Primary Key) <--- FKs reference this!
                                                role (SQLEnum UserRole)
```

### Luồng Đồng bộ Lần Đăng nhập Đầu tiên (Just-In-Time Provisioning Flow):
1. Người dùng đăng nhập thành công trên Keycloak, Frontend gửi Access Token chứa claim `sub` (Keycloak User ID UUID) và `email` tới Backend FastAPI.
2. Backend kiểm tra tính hợp lệ của Token qua JWKS của Keycloak.
3. Backend truy vấn local DB:
   ```python
   user = db.query(User).filter(User.keycloak_user_id == keycloak_sub).first()
   ```
4. Nếu chưa tìm thấy theo `keycloak_user_id`, backend thực hiện tra cứu theo `email`:
   ```python
   user = db.query(User).filter(User.email == jwt_email).first()
   ```
   - **Nếu tìm thấy theo email (Tài khoản đã tồn tại trong DB legacy/seed):**  
     Cập nhật `user.keycloak_user_id = keycloak_sub` và lưu lại. Đây là thao tác liên kết tự động bản ghi cũ với tài khoản Keycloak mới.
   - **Nếu chưa tồn tại (Người dùng mới tự đăng ký qua Keycloak):**  
     Tạo mới bản ghi `User` trong PostgreSQL với các giá trị:
     - `keycloak_user_id = keycloak_sub`
     - `email = jwt_email`
     - `full_name = jwt_name or preferred_username`
     - `role = UserRole.EMPLOYEE` *(Mặc định tuyệt đối cho người dùng mới)*
     - `password_hash = "EXTERNAL_KEYCLOAK_AUTHENTICATED"` *(Không lưu password ở local DB)*
     - `is_active = True`
5. Hàm dependency `get_current_user` trả về đối tượng `User` ORM nội bộ để phục vụ toàn bộ logic nghiệp vụ tiếp theo.

---

## 7. ROLE SOURCE-OF-TRUTH DECISION (SO SÁNH CÁC PHƯƠNG ÁN NGUỒN CHÂN LÝ VÀI TRÒ)

Cần phân tích kỹ 2 phương án quản lý Role:

| Tiêu chí so sánh | Option A: Keycloak là Source of Truth cho Role | Option B: Keycloak xác thực Identity, PostgreSQL DX-Asset là Source of Truth cho Business Role (RECOMMENDED) |
| :--- | :--- | :--- |
| **Cơ chế hoạt động** | Keycloak lưu Realm/Client Roles. JWT chứa claim roles. Backend đọc role trực tiếp từ Token. | Keycloak quản lý Đăng nhập/Identity. PostgreSQL `users.role` quản lý vai trò nghiệp vụ DX-Asset. |
| **Bảo mật & Kiểm soát** | Phụ thuộc vào Keycloak Admin API hoặc gán role thủ công trên Keycloak Console. | Hệ thống Backend tự quản lý và bảo vệ nguyên tắc invariant duy nhất cho ADMIN. |
| **Đồng bộ Dữ liệu** | Phải đồng bộ 2 chiều (Sync Keycloak Roles <-> DB local) nếu muốn query trong DB. | Không cần đồng bộ role từ Keycloak. Mọi query lọc người dùng (`User.role == IT_ASSET_MANAGER`) diễn ra trực tiếp trong DB vô cùng nhanh chóng. |
| **Độ phức tạp mã nguồn** | Cao. Phải viết logic parse Keycloak Token custom mapper, gọi Keycloak REST API khi Admin đổi role. | Rất thấp, rõ ràng và dễ bảo trì. Giữ nguyên 100% logic query RBAC hiện tại của dự án. |
| **Phù hợp Demo Học thuật** | Phức tạp, dễ phát sinh lỗi khi demo nếu kết nối Keycloak Admin API bị gián đoạn. | Cực kỳ ổn định, đáp ứng hoàn hảo tiêu chí đơn giản, tin cậy và minh bạch. |

> **QUYẾT ĐỊNH LỰA CHỌN:**  
> **Chọn OPTION B.** Keycloak chịu trách nhiệm hoàn toàn về Identity/Xác thực, còn PostgreSQL của DX-Asset giữ vai trò Source of Truth cho Business Role (`users.role`).

---

## 8. ADMIN-ONLY INVARIANT (QUY TẮC BẢO VỆ TÀI KHOẢN ADMIN DUY NHẤT)

Theo yêu cầu nghiệp vụ bắt buộc của dự án DX-Asset:

### 8.1 Tài khoản System Owner Duy nhất
Tài khoản **ADMIN duy nhất** của toàn bộ hệ thống là:
```text
2424801030008@student.tdmu.edu.vn
```

### 8.2 Các Ràng buộc Nguyên tắc (Invariants) Server-Side
1. **Không cho phép tạo thêm ADMIN**:
   - Mọi người dùng tự đăng ký (Self-registration) đều có vai trò mặc định là `EMPLOYEE`.
   - Admin có quyền nâng quyền nhân viên từ `EMPLOYEE` -> `MANAGER` hoặc `IT_ASSET_MANAGER`, và hạ quyền ngược lại.
   - Tuy nhiên, API quản lý role sẽ **CHẶN TUYỆT ĐỐI** việc nâng bất kỳ tài khoản nào khác thành `ADMIN`.
2. **Bảo vệ tài khoản System Owner khỏi bị hạ quyền hoặc xóa**:
   - Tài khoản `2424801030008@student.tdmu.edu.vn` được gắn vai trò `ADMIN` ở cấp cơ sở dữ liệu khởi tạo.
   - Mọi nỗ lực hạ quyền (`demote`), vô hiệu hóa (`is_active = False`) hoặc xóa tài khoản này qua API sẽ bị hệ thống từ chối lập tức với lỗi `HTTP 400 Bad Request`.
3. **Mã nguồn Kiểm soát (Logic Backend dự kiến)**:
   ```python
   def update_user_role(target_user: User, new_role: UserRole, current_user: User):
       if new_role == UserRole.ADMIN:
           raise HTTPException(status_code=400, detail="Không được phép gán vai trò ADMIN. Hệ thống chỉ cho phép duy nhất một System Owner ADMIN.")
       if target_user.email == "2424801030008@student.tdmu.edu.vn" and new_role != UserRole.ADMIN:
           raise HTTPException(status_code=400, detail="Không thể hạ quyền của System Owner ADMIN.")
       target_user.role = new_role
   ```

---

## 9. SELF-REGISTRATION DESIGN (THIẾT KẾ ĐĂNG KÝ TỰ DO)

Cơ chế đăng ký người dùng mới được thực hiện thông qua giao diện Self-Registration native của Keycloak:

```text
[Giao diện Đăng ký Keycloak]
          │
          ▼ 1. Người dùng nhập thông tin (Email, Password, Họ tên)
[Keycloak Realm: dx-asset]
          │
          ▼ 2. Keycloak tạo Identity và xác nhận Email (nếu bật)
[Đăng nhập thành công -> Trả JWT về Frontend]
          │
          ▼ 3. Frontend gửi Token tới FastAPI /auth/me
[FastAPI JIT Provisioning]
          │
          ▼ 4. Backend kiểm tra và tạo bản ghi local `users` với role = EMPLOYEE
[Bản ghi Local User hoàn tất với vai trò EMPLOYEE]
```

- **Quy tắc an toàn**: Frontend không được phép gửi payload dạng `{"role": "ADMIN"}` khi đăng ký. Vai trò ban đầu được ấn định cứng ở backend là `EMPLOYEE`.

---

## 10. EMAIL POLICY & DOMAIN ENFORCEMENT (CHÍNH SÁCH EMAIL VÀ TÊN MIỀN TDMU)

### 10.1 Định hướng Tên miền Chính thức
- Email sinh viên / cán bộ chính thức: `@student.tdmu.edu.vn` hoặc `@tdmu.edu.vn`.

### 10.2 Đề xuất Cấu hình Keycloak & Môi trường Development
1. **Môi trường Development / Demo**:
   - Cấu hình biến môi trường Backend: `ALLOWED_EMAIL_DOMAINS="student.tdmu.edu.vn,tdmu.edu.vn,dxasset.local"`.
   - Cho phép các tài khoản demo cũ (`admin@dxasset.local`, `it_manager@dxasset.local`,...) tiếp tục hoạt động song song để không làm hỏng các script test tự động.
2. **Cấu hình Trực tiếp trên Keycloak Realm**:
   - Sử dụng tính năng "Email as Username" trong Keycloak để đảm bảo địa chỉ Email là duy nhất và làm username chính.
   - Có thể cấu hình "Valid Redirect URIs" và "Web Origins" chặt chẽ trên Keycloak Client.
   - Tính năng Email Verification có thể tắt (`Verify Email = False`) trong môi trường Dev để đơn giản hóa kiểm thử, và bật khi triển khai thực tế.

---

## 11. OIDC CLIENT DESIGN (THIẾT KẾ CLIENT VÀ XÁC THỰC TOKEN)

### 11.1 Cấu hình Keycloak Realm & Client
- **Realm Name**: `dx-asset`
- **Client ID**: `dx-asset-frontend`
- **Client Type**: Public (Standard Flow + Authorization Code with PKCE enabled).
- **Valid Redirect URIs**: `http://localhost:3000/*`, `http://127.0.0.1:3000/*`
- **Web Origins**: `http://localhost:3000`, `http://127.0.0.1:3000`

### 11.2 Xác thực Keycloak JWT tại FastAPI Backend
FastAPI Backend đóng vai trò Resource Server xác thực Bearer token từ Keycloak:
- **Issuer (iss)**: `http://localhost:8080/realms/dx-asset`
- **JWKS Endpoint**: `http://localhost:8080/realms/dx-asset/protocol/openid-connect/certs`
- **Thuật toán chữ ký**: `RS256` (Asymmetric RSA Public/Private Key). Backend chỉ sử dụng Public Key từ JWKS Endpoint để giải mã và kiểm tra chữ ký mà không cần lưu khóa bí mật `SECRET_KEY` đối xứng.
- **Kiểm tra Token hợp lệ**:
  1. Kiểm tra chữ ký bằng JWKS.
  2. Kiểm tra `iss` trùng khớp với `KEYCLOAK_ISSUER`.
  3. Kiểm tra `exp` (chưa hết hạn).
  4. Trích xuất claim `sub` và `email`.

---

## 12. DOCKER & LOCAL DEVELOPMENT DESIGN (THIẾT KẾ DOCKER CHẠY LOCAL)

Bổ sung service `keycloak` vào file `docker-compose.yml` để chạy thống nhất môi trường development:

```yaml
  keycloak:
    image: quay.io/keycloak/keycloak:24.0.5
    container_name: dx_asset_keycloak
    restart: always
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin_password_secret
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/${POSTGRES_DB:-dx_asset_db}
      KC_DB_USERNAME: ${POSTGRES_USER:-dx_user}
      KC_DB_PASSWORD: ${POSTGRES_PASSWORD:-dx_password_secret}
      KC_DB_SCHEMA: keycloak
    command: start-dev --import-realm
    ports:
      - "8080:8080"
    volumes:
      - ./docker/keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json
    depends_on:
      postgres:
        condition: service_healthy
```

> **Lưu ý**: Phiên bản Keycloak được ghim cố định là `24.0.5` (tránh dùng tag `:latest` gây mất ổn định khi build lại).

---

## 13. USER MIGRATION PLAN (KẾ HOẠCH MIGRATION DỮ LIỆU NGƯỜI DÙNG)

Để đảm bảo toàn bộ dữ liệu lịch sử, cấp phát, sự cố, kỹ năng và Process Mining không bị mất mát hoặc đứt gãy liên kết:

### 13.1 Các tài khoản Demo Cũ & Tài khoản System Owner Mới
Danh sách tài khoản trong file `realm-export.json` khởi tạo sẵn trên Keycloak:

| Email | Password | Full Name | Local Role |
| :--- | :--- | :--- | :--- |
| `2424801030008@student.tdmu.edu.vn` | `password123` | Nguyễn Phạm Đại Phúc (System Owner) | `ADMIN` |
| `admin@dxasset.local` | `password123` | Nguyễn Văn Admin | `ADMIN` |
| `it_manager@dxasset.local` | `password123` | Trần Thị IT Manager | `IT_ASSET_MANAGER` |
| `manager@dxasset.local` | `password123` | Lê Văn Manager | `MANAGER` |
| `employee1@dxasset.local` | `password123` | Nguyễn Văn A (Sales) | `EMPLOYEE` |
| `employee2@dxasset.local` | `password123` | Phạm Thị B (HR) | `EMPLOYEE` |

### 13.2 Quy trình Migration không làm mất khóa ngoại
1. **Bước 1**: Chạy Alembic Migration để thêm cột `keycloak_user_id` vào bảng `users`.
2. **Bước 2**: Khởi chạy Keycloak container với file `realm-export.json`.
3. **Bước 3**: Chạy script seed data nâng cấp (`scripts/seed_data.py`) để thêm tài khoản `2424801030008@student.tdmu.edu.vn` vào local DB nếu chưa có.
4. **Bước 4**: Khi người dùng hoặc demo account đăng nhập lần đầu qua Keycloak OIDC, cơ chế JIT Sync sẽ tự động map `keycloak_user_id` vào bản ghi local `users` tương ứng dựa trên `email`.
5. **Kết quả**: Tất cả `users.id` nội bộ giữ nguyên 100%, các liên kết FK ở `asset_assignments`, `incidents`, `maintenances`, `process_events` hoàn toàn nguyên vẹn!

---

## 14. API COMPATIBILITY AUDIT (PHÂN LOẠI ẢNH HƯỞNG API)

Tất cả API endpoint của hệ thống được kiểm tra và phân thành 4 nhóm ảnh hưởng:

### Nhóm A: KHÔNG CẦN SỬA (Giữ nguyên 100%)
- `GET /api/v1/health`
- `GET /api/v1/departments`

### Nhóm B: CẦN SỬA AUTHENTICATION (Logic nghiệp vụ giữ nguyên)
- `GET /api/v1/assets`, `GET /api/v1/assets/{id}`, `GET /api/v1/assets/code/{code}`
- `GET /api/v1/assignments`, `GET /api/v1/assignments/my-assets`
- `GET /api/v1/incidents`, `GET /api/v1/incidents/{id}`
- `GET /api/v1/maintenances`, `GET /api/v1/maintenances/{id}`
- `GET /api/v1/dashboard/summary`, `GET /api/v1/dashboard/recent-activities`
- `POST /api/v1/assistant/chat`
- Các endpoint phân tích trí tuệ: `GET /api/v1/intelligence/*`
- Các endpoint mô phỏng tối ưu: `POST /api/v1/optimization/*`
- Các endpoint Process Mining: `GET /api/v1/process-mining/*`
*(Tất cả nhóm này chỉ thay đổi cơ chế xác thực JWT nội bộ sang giải mã Keycloak JWT RS256 thông qua `get_current_user`)*.

### Nhóm C: CẦN SỬA ROLE HANDLING & CHỨC NĂNG CỦA ADMIN
- `GET /api/v1/users`: Trả về danh sách người dùng đã gắn `keycloak_user_id`.
- `GET /api/v1/users/technicians/skills`, `POST /api/v1/users/{id}/skills`
- **Bổ sung endpoint mới**: `PUT /api/v1/users/{id}/role` (Thay đổi role người dùng, áp dụng chặt chẽ quy tắc bảo vệ ADMIN duy nhất).

### Nhóm D: NGUY CƠ BỊ ẢNH HƯỞNG & CẦN CẬP NHẬT LUỒNG AUTH
- `POST /api/v1/auth/login`: Chuyển sang xác thực ủy quyền hoặc dùng Keycloak Token Exchange.
- `GET /api/v1/auth/me`: Nhận Bearer token từ Keycloak, kích hoạt JIT Sync và trả về thông tin `UserResponse` cùng vai trò local.

---

## 15. TEST IMPACT ANALYSIS (ẢNH HƯỞNG TỚI BỘ TEST SUITE)

### 15.1 Các Test bị ảnh hưởng hiện tại
Các file test đang phụ thuộc trực tiếp vào hàm `create_access_token` và mật khẩu Bcrypt local:
- [backend/tests/test_auth.py](file:///D:/web/dx-asset/backend/tests/test_auth.py)
- [backend/tests/test_rbac.py](file:///D:/web/dx-asset/backend/tests/test_rbac.py)
- [backend/tests/conftest.py](file:///D:/web/dx-asset/backend/tests/conftest.py)

### 15.2 Giải pháp Migration Test Suite (Phase 16H)
- Tạo một **Mock JWKS Decoder / Test Key Pair Generator** trong Pytest `conftest.py`.
- Khi chạy unit test bằng Pytest, hàm `get_current_user` sẽ giải mã RSA test token mà không cần bắt buộc phải bật container Keycloak thật. Điều này giúp bộ test chạy cực kỳ nhanh, độc lập và ổn định (CI/CD friendly).

---

## 16. SECURITY AUDIT (AUDIT BẢO MẬT KHẮT KHE)

1. **Chống giả mạo vai trò (Role Spoofing Prevention)**:
   - Dù người dùng có tự sửa Token hay gửi thông tin vai trò ở Frontend payload, Backend FastAPI **HOÀN TOÀN KHÔNG TIN NGUỒN FRONTEND**.
   - Backend luôn lấy đối tượng `User` từ database PostgreSQL local (nơi giữ Source of Truth cho Role) dựa trên `keycloak_user_id` đã được xác thực chữ ký RS256.
2. **Chống leo thang đặc quyền (Privilege Escalation Prevention)**:
   - Không có API nào cho phép chọn vai trò `ADMIN`.
   - Mọi tài khoản tự đăng ký qua Keycloak chỉ nhận được vai trò `EMPLOYEE`.
3. **Bảo mật JWT RS256**:
   - Sử dụng thuật toán bất đối xứng RS256. Public Key được tự động truy xuất và verify qua Keycloak JWKS Endpoint.
   - Token hết hạn hoặc chữ ký không hợp lệ bị từ chối ngay lập tức từ tầng dependency `get_current_user`.

---

## 17. MIGRATION RISKS & MITIGATION STRATEGY (RỦI RO VÀ GIẢI PHÁP)

| Rủi ro kỹ thuật | Mức độ | Giải pháp khắc phục (Mitigation) |
| :--- | :--- | :--- |
| **Gián đoạn kết nối tới Keycloak JWKS Endpoint** | Trung bình | Implement bộ nhớ đệm Cache in-memory cho JWKS public keys tại Backend với TTL 24h và tự động retry khi gặp lỗi mạng. |
| **Không trùng khớp Email giữa tài khoản cũ và Keycloak** | Thấp | Ép kiểu Email về `lowercase` và loại bỏ khoảng trắng thừa khi tra cứu JIT sync. |
| **Lỗi khởi động Keycloak do thiếu RAM/Resource** | Thấp | Cấu hình giới hạn tài nguyên hợp lý trong Docker Compose, ghin cố định image `keycloak:24.0.5`. |

---

## 18. IMPLEMENTATION PLAN FOR PHASE 16B - 16J (KẾ HOẠCH TRIỂN KHAI TỪNG BƯỚC)

Chi tiết các bước thực hiện tiếp theo (Chỉ triển khai khi được người dùng yêu cầu tiếp tục):

- **Phase 16B — Keycloak Docker Infrastructure & Realm Pre-configuration**:  
  Cập nhật `docker-compose.yml`, tạo file cấu hình realm export `docker/keycloak/realm-export.json`.
- **Phase 16C — Backend Keycloak OIDC & JWKS JWT Verification**:  
  Cập nhật `app/core/security.py` và `app/api/deps.py` để hỗ trợ xác thực chữ ký RS256 qua JWKS.
- **Phase 16D — Database Schema Migration for `keycloak_user_id`**:  
  Tạo Alembic Migration bổ sung cột `keycloak_user_id` vào bảng `users`.
- **Phase 16E — Backend User JIT Synchronization & Link Flow**:  
  Cập nhật `/auth/me` và dịch vụ đồng bộ người dùng tự động lần đăng nhập đầu tiên.
- **Phase 16F — Admin Invariant Enforcement & Role Management API**:  
  Cập nhật `app/api/v1/users.py` với logic bảo vệ System Owner `2424801030008@student.tdmu.edu.vn`.
- **Phase 16G — Frontend Integration with Keycloak OIDC**:  
  Cập nhật `auth-context.tsx`, `api.ts`, trang `login/page.tsx` kết nối với Keycloak OIDC.
- **Phase 16H — Test Suite Migration & Mock Authentication**:  
  Cập nhật `tests/conftest.py`, `test_auth.py`, `test_rbac.py` với RS256 mock client.
- **Phase 16I — Seed Script & Documentation Update**:  
  Cập nhật `scripts/seed_data.py` bổ sung tài khoản System Owner `2424801030008@student.tdmu.edu.vn`.
- **Phase 16J — End-to-End Verification & Final Acceptance**:  
  Kiểm thử toàn bộ 10 bước workflow nghiệp vụ chính và xác nhận hoàn tất Phase 16.

---

## 19. FILES EXPECTED TO CHANGE (DANH SÁCH FILE SẼ THAY ĐỔI Ở CÁC PHASE SAU)

- `docker-compose.yml`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/api/deps.py`
- `backend/app/models/user.py`
- `backend/app/schemas/user.py`
- `backend/app/api/v1/auth.py`
- `backend/app/api/v1/users.py`
- `scripts/seed_data.py`
- `backend/tests/conftest.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_rbac.py`
- `frontend/src/lib/auth-context.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/app/login/page.tsx`

---

## 20. FILES THAT MUST NOT BE CHANGED (DANH SÁCH FILE TUYỆT ĐỐI KHÔNG ĐƯỢC THAY ĐỔI)

- Các ORM model nghiệp vụ cốt lõi:
  - `backend/app/models/asset.py`
  - `backend/app/models/assignment.py`
  - `backend/app/models/incident.py`
  - `backend/app/models/maintenance.py`
  - `backend/app/models/history.py`
  - `backend/app/models/department.py`
  - `backend/app/models/process_case.py`
  - `backend/app/models/process_event.py`
- Các dịch vụ thuật toán nghiệp vụ:
  - `backend/app/services/smart_routing.py`
  - `backend/app/api/v1/intelligence.py`
  - `backend/app/api/v1/optimization.py`
  - `backend/app/api/v1/process_mining.py`
- Kiểu dữ liệu và các khóa ngoại Foreign Key trỏ tới `users.id` trong cơ sở dữ liệu.

---

## 21. ACCEPTANCE CRITERIA CHECKLIST (DẠNG KIỂM TRA HOÀN THÀNH PHASE 16A)

- [x] Hiểu đầy đủ kiến trúc authentication hiện tại
- [x] Hiểu đầy đủ cấu trúc bảng `users` và các quan hệ khóa ngoại (FKs)
- [x] Hiểu đầy đủ mô hình RBAC 4 vai trò
- [x] Hiểu đầy đủ luồng xác thực trên Frontend
- [x] Xác định mô hình Identity Mapping liên kết `keycloak_user_id` với `users.id`
- [x] Xác định Option B là Source of Truth cho vai trò nghiệp vụ (PostgreSQL DX-Asset)
- [x] Có cơ chế bảo vệ Server-side cho duy nhất một tài khoản System Owner `2424801030008@student.tdmu.edu.vn`
- [x] Thiết kế luồng Self-Registration với vai trò mặc định `EMPLOYEE`
- [x] Đề xuất Email Policy phù hợp với tên miền TDMU và môi trường Dev
- [x] Thiết kế OIDC Client & cơ chế xác thực JWT RS256 qua Keycloak JWKS
- [x] Thiết kế Docker Compose service cho Keycloak stable version `24.0.5`
- [x] Có kế hoạch User Migration chi tiết đảm bảo vẹn toàn dữ liệu lịch sử và khóa ngoại
- [x] Phân loại ảnh hưởng API (Nhóm A, B, C, D)
- [x] Đánh giá ảnh hưởng bộ Test suite và giải pháp Mock Test Pytest
- [x] Phân tích an toàn bảo mật (Role spoofing, Privilege escalation)
- [x] Không làm thay đổi feature code ở Phase 16A
- [x] Không commit hoặc push code

---

```text
PHASE 16A STATUS: READY FOR IMPLEMENTATION
```
