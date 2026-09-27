# HƯỚNG DẪN CẤU HÌNH VÀ VẬN HÀNH OLLAMA LOCAL AI (DX-ASSET)

## 📌 Giới thiệu Ollama trong DX-Asset

**Ollama** được tích hợp vào nền tảng **DX-Asset** dưới dạng một **Local LLM Service** chạy độc lập trong Docker Compose. Dịch vụ này cho phép Trợ lý AI diễn giải dữ liệu quản lý tài sản và trả lời câu hỏi của người dùng bằng tiếng Việt tự nhiên, trực quan theo chuẩn Markdown mà **không phụ thuộc vào bất kỳ API key của bên thứ 3 nào (như OpenAI)** và **không lo lộ dữ liệu doanh nghiệp ra ngoài**.

---

## 🏛️ Kiến trúc & Luồng xử lý An toàn (Security Data Flow)

```text
User 
  │ (Gửi câu hỏi tiếng Việt)
  ▼
Next.js App (Frontend)
  │ (POST /api/v1/assistant/chat + JWT Token)
  ▼
FastAPI Backend
  │ 
  ├── 1. Xác thực JWT & Kiểm tra Phân quyền RBAC (Role-Based Access Control)
  ├── 2. Chặn các thao tác Mutation (xóa/sửa/tạo mới) -> Trả về MUTATION_REJECTED
  ├── 3. Xử lý các Intent cố định (Process Mining, Optimization Simulation)
  ├── 4. Truy vấn dữ liệu thực tế từ CSDL PostgreSQL (lọc theo phạm vi người dùng)
  └── 5. Đóng gói dữ liệu thật thành Structured Context (KHÔNG chứa DB credentials/secrets)
        │
        ▼
  Ollama Container (http://ollama:11434/api/chat)
        │ (Sử dụng Model qwen2.5:3b để tổng hợp & diễn giải dữ liệu)
        ▼
FastAPI Backend ──► Next.js Frontend ──► Trả về kết quả tự nhiên cho User
```

> ⚠️ **Nguyên tắc an toàn**:
> - Ollama **KHÔNG** có quyền truy cập trực tiếp vào PostgreSQL.
> - Ollama **KHÔNG** có quyền tự tạo hay thực thi câu lệnh SQL.
> - Ollama **KHÔNG** nhận mật khẩu, bí mật kết nối hay API secrets.
> - Nếu Ollama bị dừng, timeout hoặc lỗi, Backend sẽ **tự động Fallback mượt mà sang Rule-Based Engine** (`is_fallback: true`) để đảm bảo hệ thống không bao giờ bị đơ hay sập.

---

## 🛠️ Cấu hình Docker Compose & Biến Môi trường

### 1. Dịch vụ Ollama trong `docker-compose.yml`
```yaml
  ollama:
    image: ollama/ollama:latest
    container_name: dx_asset_ollama
    restart: always
    ports:
      - "11434:11434"
    volumes:
      - ollama_storage:/root/.ollama
    environment:
      - OLLAMA_KEEP_ALIVE=24h
      - OLLAMA_NUM_PARALLEL=2
    healthcheck:
      test: ["CMD-SHELL", "exec 3<>/dev/tcp/127.0.0.1/11434"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 15s
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

### 2. Biến môi trường trong `.env`
```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT_SECONDS=10
```

---

## 🚀 Hướng dẫn Khởi chạy & Tải Model

### Bước 1: Khởi chạy các container bằng Docker Compose
```bash
docker compose up -d
```

### Bước 2: Tải Model `qwen2.5:3b` vào Ollama Container (Lần đầu tiên)
```bash
docker exec -it dx_asset_ollama ollama pull qwen2.5:3b
```
*(Model dung lượng ~1.9 GB sẽ được tải và lưu bền vững vào Docker Volume `ollama_storage`, các lần restart sau không cần tải lại).*

---

## 📊 Các Lệnh Kiểm tra & Quản trị Ollama

- **Kiểm tra danh sách Model đã tải**:
  ```bash
  docker exec dx_asset_ollama ollama list
  ```
- **Kiểm tra trạng thái Container**:
  ```bash
  docker compose ps ollama
  ```
- **Xem nhật ký hoạt động (Logs)**:
  ```bash
  docker compose logs -f --tail=100 ollama
  ```
- **Khởi động lại dịch vụ Ollama**:
  ```bash
  docker compose restart ollama
  ```

---

## 💡 Ghi chú về Phần cứng (CPU & GPU)

- **Nếu máy có GPU NVIDIA (như RTX 3050 / 3060...)**:
  Ollama sẽ tự động sử dụng GPU qua Docker WSL2 GPU passthrough. Model `qwen2.5:3b` chiếm ~2.2 GB VRAM, phản hồi cực kỳ nhanh (~40-60 tokens/giây).
- **Nếu máy chỉ có CPU**:
  Ollama tự động fallback chạy trên CPU (x86_64 AVX2) mà không báo lỗi. Trên CPU đa nhân, model 3B vẫn cho tốc độ phản hồi mượt mà.

---

## 📦 Khi Đóng gói sang Máy khác

Khi giải nén mã nguồn hoặc clone sang máy khác:
1. Chạy `docker compose up -d`.
2. Chạy 1 lệnh pull model: `docker exec -it dx_asset_ollama ollama pull qwen2.5:3b`.
3. Hệ thống Trợ lý AI sẵn sàng phục vụ!
