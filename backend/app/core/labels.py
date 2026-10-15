"""
Vietnamese display labels for enum codes.

Codes (ASSIGNED, IN_PROGRESS, ...) stay in the database and API fields; any text built for
people to read (error messages, history details, assistant answers) uses these labels instead.
Keep in sync with frontend/src/lib/labels.ts.
"""
from enum import Enum
from typing import Any, Optional

_LABELS: dict[str, dict[str, str]] = {
    "UserRole": {
        "ADMIN": "Quản trị viên",
        "IT_ASSET_MANAGER": "Quản lý tài sản IT",
        "MANAGER": "Quản lý",
        "EMPLOYEE": "Nhân viên",
    },
    "AssetStatus": {
        "IN_STOCK": "Trong kho",
        "ASSIGNED": "Đang cấp phát",
        "IN_MAINTENANCE": "Đang bảo trì",
        "DAMAGED": "Hư hỏng",
        "RETIRED": "Đã thanh lý",
        "LOST": "Thất lạc",
        "INACTIVE": "Ngừng sử dụng",
    },
    "AssignmentStatus": {
        "ACTIVE": "Đang sử dụng",
        "RETURNED": "Đã thu hồi",
    },
    "IncidentStatus": {
        "OPEN": "Mới tạo",
        "IN_REVIEW": "Đang xem xét",
        "IN_PROGRESS": "Đang xử lý",
        "WAITING_FOR_INFO": "Chờ thông tin",
        "RESOLVED": "Đã khắc phục",
        "CLOSED": "Đã đóng",
        "CANCELLED": "Đã hủy",
    },
    "IncidentCategory": {
        "HARDWARE": "Phần cứng",
        "SOFTWARE": "Phần mềm",
        "NETWORK": "Mạng",
        "POWER": "Nguồn điện",
        "PHYSICAL_DAMAGE": "Hư hỏng vật lý",
        "OTHER": "Khác",
    },
    "IncidentPriority": {
        "LOW": "Thấp",
        "MEDIUM": "Trung bình",
        "HIGH": "Cao",
        "CRITICAL": "Khẩn cấp",
    },
    "MaintenanceStatus": {
        "SCHEDULED": "Đã lên lịch",
        "IN_PROGRESS": "Đang sửa chữa",
        "COMPLETED": "Hoàn thành",
        "CANCELLED": "Đã hủy",
    },
    "AssetActionType": {
        "CREATED": "Tạo tài sản",
        "ASSIGNED": "Cấp phát",
        "RETURNED": "Thu hồi",
        "INCIDENT_REPORTED": "Báo sự cố",
        "MAINTENANCE_STARTED": "Bắt đầu bảo trì",
        "MAINTENANCE_COMPLETED": "Hoàn thành bảo trì",
        "MAINTENANCE_UPDATED": "Cập nhật bảo trì",
        "STATUS_CHANGED": "Đổi trạng thái",
    },
    "ProcessEventType": {
        "INCIDENT_CREATED": "Tạo phiếu sự cố",
        "INCIDENT_STATUS_CHANGED": "Cập nhật trạng thái sự cố",
        "TECHNICIAN_ASSIGNED": "Phân công kỹ thuật viên",
        "MAINTENANCE_CREATED": "Tạo phiếu bảo trì",
        "MAINTENANCE_STATUS_CHANGED": "Cập nhật trạng thái bảo trì",
    },
    "ProcessCaseType": {
        "INCIDENT": "Sự cố",
        "MAINTENANCE": "Bảo trì",
    },
    "RiskLevel": {
        "LOW": "Thấp",
        "MEDIUM": "Trung bình",
        "HIGH": "Cao",
        "CRITICAL": "Nguy cấp",
    },
}

# Status strings that are not tied to one enum (e.g. process events store plain status text)
_ANY_STATUS = {
    **_LABELS["AssetStatus"],
    **_LABELS["MaintenanceStatus"],
    **_LABELS["IncidentStatus"],
}


def _code(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.value if isinstance(value, Enum) else str(value)


def vi(value: Any, kind: Optional[str] = None) -> str:
    """
    Vietnamese label for an enum member or code string.
    `kind` is the enum class name ("IncidentStatus", "RiskLevel", ...); for Enum members it is inferred.
    """
    code = _code(value)
    if code is None:
        return "Không xác định"
    kind = kind or (type(value).__name__ if isinstance(value, Enum) else None)
    if kind and code in _LABELS.get(kind, {}):
        return _LABELS[kind][code]
    return _ANY_STATUS.get(code, "Không xác định")
