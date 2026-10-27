from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.APP_NAME,
    description="API của nền tảng mã nguồn mở quản lý vòng đời tài sản DX-Asset",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Readable names for request fields that appear in validation messages
FIELD_LABELS = {
    "title": "Tiêu đề",
    "description": "Mô tả",
    "name": "Tên",
    "code": "Mã",
    "email": "Email",
    "password": "Mật khẩu",
    "asset_id": "Tài sản",
    "asset_code": "Mã tài sản",
    "category": "Phân loại",
    "priority": "Mức ưu tiên",
    "status": "Trạng thái",
    "role": "Vai trò",
    "message": "Nội dung câu hỏi",
    "technician_id": "Kỹ thuật viên",
    "assigned_to_user_id": "Người nhận",
    "department_id": "Phòng ban",
    "repair_cost": "Chi phí sửa chữa",
    "quantity": "Số lượng",
    "unit_cost": "Giá mỗi tài sản",
}

ERROR_MESSAGES = {
    "missing": "là bắt buộc",
    "string_too_short": "quá ngắn hoặc đang để trống",
    "string_too_long": "quá dài",
    "int_parsing": "phải là số nguyên",
    "float_parsing": "phải là số",
    "greater_than": "nhỏ hơn mức tối thiểu cho phép",
    "greater_than_equal": "nhỏ hơn mức tối thiểu cho phép",
    "less_than": "vượt quá mức tối đa cho phép",
    "less_than_equal": "vượt quá mức tối đa cho phép",
    "enum": "không nằm trong các lựa chọn hợp lệ",
    "literal_error": "không nằm trong các lựa chọn hợp lệ",
    "value_error": "không hợp lệ",
    "datetime_parsing": "không đúng định dạng ngày giờ",
    "date_parsing": "không đúng định dạng ngày",
    "json_invalid": "không đúng định dạng",
}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return one Vietnamese sentence instead of Pydantic's English error list."""
    messages = []
    for error in exc.errors():
        field = next((str(part) for part in reversed(error.get("loc", ())) if isinstance(part, str) and part not in ("body", "query", "path")), None)
        label = FIELD_LABELS.get(field, f"Trường \"{field}\"" if field else "Dữ liệu gửi lên")
        if error.get("type") == "value_error":
            # Custom validators already raise Vietnamese messages ("Value error, <message>")
            text = str(error.get("msg", "")).removeprefix("Value error, ")
            messages.append(text)
        else:
            messages.append(f"{label} {ERROR_MESSAGES.get(error.get('type'), 'không hợp lệ')}.")
    unique = list(dict.fromkeys(messages))
    return JSONResponse(status_code=422, content={"detail": "Dữ liệu không hợp lệ: " + " ".join(unique)})


# Include v1 Router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "message": f"Chào mừng đến với API {settings.APP_NAME}",
        "docs": "/docs",
        "status": "online"
    }
