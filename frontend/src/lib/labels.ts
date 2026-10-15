// Vietnamese display labels for the system's internal codes.
// The API keeps stable machine codes (ASSIGNED, IN_PROGRESS, ...); users only ever see these labels.

export const ROLE_LABELS: Record<string, string> = {
  ADMIN: 'Quản trị viên',
  IT_ASSET_MANAGER: 'Quản lý tài sản IT',
  MANAGER: 'Quản lý',
  EMPLOYEE: 'Nhân viên',
};

export const ASSET_STATUS_LABELS: Record<string, string> = {
  IN_STOCK: 'Trong kho',
  ASSIGNED: 'Đang cấp phát',
  IN_MAINTENANCE: 'Đang bảo trì',
  DAMAGED: 'Hư hỏng',
  RETIRED: 'Đã thanh lý',
  LOST: 'Thất lạc',
  INACTIVE: 'Ngừng sử dụng',
};

export const INCIDENT_STATUS_LABELS: Record<string, string> = {
  OPEN: 'Mới tạo',
  IN_REVIEW: 'Đang xem xét',
  IN_PROGRESS: 'Đang xử lý',
  WAITING_FOR_INFO: 'Chờ thông tin',
  RESOLVED: 'Đã khắc phục',
  CLOSED: 'Đã đóng',
  CANCELLED: 'Đã hủy',
};

export const INCIDENT_CATEGORY_LABELS: Record<string, string> = {
  HARDWARE: 'Phần cứng',
  SOFTWARE: 'Phần mềm',
  NETWORK: 'Mạng',
  POWER: 'Nguồn điện',
  PHYSICAL_DAMAGE: 'Hư hỏng vật lý',
  OTHER: 'Khác',
};

export const PRIORITY_LABELS: Record<string, string> = {
  LOW: 'Thấp',
  MEDIUM: 'Trung bình',
  HIGH: 'Cao',
  CRITICAL: 'Khẩn cấp',
};

export const MAINTENANCE_STATUS_LABELS: Record<string, string> = {
  SCHEDULED: 'Đã lên lịch',
  IN_PROGRESS: 'Đang sửa chữa',
  COMPLETED: 'Hoàn thành',
  CANCELLED: 'Đã hủy',
};

export const ASSIGNMENT_STATUS_LABELS: Record<string, string> = {
  ACTIVE: 'Đang sử dụng',
  RETURNED: 'Đã thu hồi',
};

export const ASSET_ACTION_LABELS: Record<string, string> = {
  CREATED: 'Tạo tài sản',
  ASSIGNED: 'Cấp phát',
  RETURNED: 'Thu hồi',
  INCIDENT_REPORTED: 'Báo sự cố',
  MAINTENANCE_STARTED: 'Bắt đầu bảo trì',
  MAINTENANCE_COMPLETED: 'Hoàn thành bảo trì',
  MAINTENANCE_UPDATED: 'Cập nhật bảo trì',
  STATUS_CHANGED: 'Đổi trạng thái',
};

export const RISK_LEVEL_LABELS: Record<string, string> = {
  CRITICAL: 'Nguy cấp',
  HIGH: 'Cao',
  MEDIUM: 'Trung bình',
  LOW: 'Thấp',
};

// Support queues suggested by smart routing
export const QUEUE_LABELS: Record<string, string> = {
  HARDWARE_SUPPORT: 'Nhóm hỗ trợ phần cứng',
  SOFTWARE_SUPPORT: 'Nhóm hỗ trợ phần mềm',
  NETWORK_SUPPORT: 'Nhóm hỗ trợ mạng',
  INFRASTRUCTURE_SUPPORT: 'Nhóm hạ tầng & điện',
  GENERAL_SUPPORT: 'Nhóm hỗ trợ chung',
};

function lookup(map: Record<string, string>, code: string | null | undefined): string {
  if (!code) return '—';
  return map[code] ?? 'Không xác định';
}

export const roleLabel = (code?: string | null) => lookup(ROLE_LABELS, code);
export const assetStatusLabel = (code?: string | null) => lookup(ASSET_STATUS_LABELS, code);
export const incidentStatusLabel = (code?: string | null) => lookup(INCIDENT_STATUS_LABELS, code);
export const incidentCategoryLabel = (code?: string | null) => lookup(INCIDENT_CATEGORY_LABELS, code);
export const priorityLabel = (code?: string | null) => lookup(PRIORITY_LABELS, code);
export const maintenanceStatusLabel = (code?: string | null) => lookup(MAINTENANCE_STATUS_LABELS, code);
export const assignmentStatusLabel = (code?: string | null) => lookup(ASSIGNMENT_STATUS_LABELS, code);
export const assetActionLabel = (code?: string | null) => lookup(ASSET_ACTION_LABELS, code);
export const riskLevelLabel = (code?: string | null) => lookup(RISK_LEVEL_LABELS, code);
export const queueLabel = (code?: string | null) => lookup(QUEUE_LABELS, code);
