"""
DX-Asset - Seed Data Script (Idempotent)
Mục đích: Nạp dữ liệu khởi tạo ban đầu (Departments, Users, Assets, Assignments, Incidents, Histories) vào PostgreSQL.
An toàn: Có thể chạy lặp lại nhiều lần mà không tạo bản ghi trùng hoặc lỗi duy nhất.
"""
import os
import sys
import logging
from datetime import datetime, timezone

# Ensure app is importable
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models import (
    Department,
    User,
    Asset,
    AssetAssignment,
    Incident,
    AssetHistory,
    TechnicianSkill,
    UserRole,
    AssetStatus,
    AssignmentStatus,
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
    AssetActionType,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def seed_database():
    db = SessionLocal()
    try:
        logger.info("==================================================")
        logger.info("BẮT ĐẦU NẠP DỮ LIỆU MẪU CHO DX-ASSET (IDEMPOTENT)")
        logger.info("==================================================")

        # 1. SEED DEPARTMENTS
        departments_data = [
            {"code": "IT", "name": "Phòng Công nghệ Thông tin", "description": "Quản lý hạ tầng IT và hỗ trợ kỹ thuật"},
            {"code": "HR", "name": "Phòng Nhân sự", "description": "Quản lý nhân sự và tuyển dụng"},
            {"code": "FINANCE", "name": "Phòng Tài chính Kế toán", "description": "Quản lý ngân sách và tài chính"},
            {"code": "ADMINISTRATION", "name": "Phòng Hành chính Quản trị", "description": "Quản lý văn phòng và thiết bị nội bộ"},
            {"code": "SALES", "name": "Phòng Kinh doanh", "description": "Phát triển thị trường và bán hàng"},
        ]
        
        dept_map = {}
        depts_created = 0
        for d in departments_data:
            existing = db.query(Department).filter(Department.code == d["code"]).first()
            if not existing:
                dept = Department(**d)
                db.add(dept)
                db.flush()
                dept_map[d["code"]] = dept
                depts_created += 1
            else:
                dept_map[d["code"]] = existing

        logger.info(f"-> Departments: Đã tạo {depts_created} mới, tổng số: {len(dept_map)}")

        # 2. SEED USERS
        common_password_hash = get_password_hash("password123")
        users_data = [
            {
                "email": "2424801030008@student.tdmu.edu.vn",
                "full_name": "Nguyễn Phạm Đại Phúc (System Owner)",
                "role": UserRole.ADMIN,
                "dept_code": "ADMINISTRATION",
            },
            {
                "email": "admin@dxasset.local",
                "full_name": "Nguyễn Văn Admin (Legacy)",
                "role": UserRole.IT_ASSET_MANAGER,
                "dept_code": "ADMINISTRATION",
            },
            {
                "email": "it_manager@dxasset.local",
                "full_name": "Trần Thị IT Manager",
                "role": UserRole.IT_ASSET_MANAGER,
                "dept_code": "IT",
            },
            {
                "email": "manager@dxasset.local",
                "full_name": "Lê Văn Manager",
                "role": UserRole.MANAGER,
                "dept_code": "SALES",
            },
            {
                "email": "employee1@dxasset.local",
                "full_name": "Nguyễn Văn A (Sales)",
                "role": UserRole.EMPLOYEE,
                "dept_code": "SALES",
            },
            {
                "email": "employee2@dxasset.local",
                "full_name": "Phạm Thị B (HR)",
                "role": UserRole.EMPLOYEE,
                "dept_code": "HR",
            },
        ]

        user_map = {}
        users_created = 0
        for u in users_data:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                user = User(
                    email=u["email"],
                    password_hash=common_password_hash,
                    full_name=u["full_name"],
                    role=u["role"],
                    department_id=dept_map[u["dept_code"]].id,
                    is_active=True,
                )
                db.add(user)
                db.flush()
                user_map[u["email"]] = user
                users_created += 1
            else:
                existing.role = u["role"]
                existing.is_active = True
                user_map[u["email"]] = existing

        logger.info(f"-> Users: Đã tạo {users_created} mới, tổng số: {len(user_map)}")

        # 3. SEED ASSETS
        assets_data = [
            {
                "asset_code": "LAP-001",
                "name": "Laptop Lenovo ThinkPad X1 Carbon",
                "category": "Laptop",
                "brand": "Lenovo",
                "model": "ThinkPad X1",
                "serial_number": "SN-THINKPAD-001",
                "status": AssetStatus.ASSIGNED,
                "dept_code": "SALES",
                "location": "Tầng 3 - Phòng Sales",
                "current_user_email": "employee1@dxasset.local",
            },
            {
                "asset_code": "LAP-002",
                "name": "Laptop Dell XPS 15",
                "category": "Laptop",
                "brand": "Dell",
                "model": "XPS 15 9530",
                "serial_number": "SN-DELLXPS-002",
                "status": AssetStatus.IN_STOCK,
                "dept_code": "IT",
                "location": "Kho IT Tầng 2",
                "current_user_email": None,
            },
            {
                "asset_code": "PC-001",
                "name": "Desktop PC Workstation HP Z4",
                "category": "Desktop PC",
                "brand": "HP",
                "model": "Z4 G4",
                "serial_number": "SN-HPZ4-003",
                "status": AssetStatus.ASSIGNED,
                "dept_code": "HR",
                "location": "Tầng 2 - Phòng HR",
                "current_user_email": "employee2@dxasset.local",
            },
            {
                "asset_code": "MON-001",
                "name": "Màn hình Dell UltraSharp 27 inch",
                "category": "Monitor",
                "brand": "Dell",
                "model": "U2723QE",
                "serial_number": "SN-DELLMON-004",
                "status": AssetStatus.ASSIGNED,
                "dept_code": "SALES",
                "location": "Tầng 3 - Bàn Sales A",
                "current_user_email": "employee1@dxasset.local",
            },
            {
                "asset_code": "PRN-001",
                "name": "Máy in Laser Canon LBP2900",
                "category": "Printer",
                "brand": "Canon",
                "model": "LBP2900",
                "serial_number": "SN-CANON-005",
                "status": AssetStatus.IN_STOCK,
                "dept_code": "ADMINISTRATION",
                "location": "Phòng Hành chính Tầng 1",
                "current_user_email": None,
            },
            {
                "asset_code": "SWT-001",
                "name": "Switch Cisco Catalyst 24 Port",
                "category": "Network Switch",
                "brand": "Cisco",
                "model": "C2960X",
                "serial_number": "SN-CISCO-006",
                "status": AssetStatus.IN_STOCK,
                "dept_code": "IT",
                "location": "Phòng Server Tầng 2",
                "current_user_email": None,
            },
            {
                "asset_code": "KB-001",
                "name": "Bàn phím cơ Logitech MX Keys",
                "category": "Keyboard",
                "brand": "Logitech",
                "model": "MX Keys",
                "serial_number": "SN-LOGI-007",
                "status": AssetStatus.IN_MAINTENANCE,
                "dept_code": "IT",
                "location": "Phòng Bảo trì IT",
                "current_user_email": None,
            },
        ]

        asset_map = {}
        assets_created = 0
        for a in assets_data:
            existing = db.query(Asset).filter(Asset.asset_code == a["asset_code"]).first()
            current_user_id = user_map[a["current_user_email"]].id if a["current_user_email"] else None
            dept_id = dept_map[a["dept_code"]].id if a["dept_code"] else None
            
            if not existing:
                asset = Asset(
                    asset_code=a["asset_code"],
                    name=a["name"],
                    category=a["category"],
                    brand=a["brand"],
                    model=a["model"],
                    serial_number=a["serial_number"],
                    status=a["status"],
                    department_id=dept_id,
                    current_user_id=current_user_id,
                    location=a["location"],
                    description=f"Thiết bị mẫu {a['name']} cấp cho doanh nghiệp.",
                    qr_code_url=f"/assets/{a['asset_code']}",
                )
                db.add(asset)
                db.flush()
                asset_map[a["asset_code"]] = asset
                assets_created += 1
            else:
                asset_map[a["asset_code"]] = existing

        logger.info(f"-> Assets: Đã tạo {assets_created} mới, tổng số: {len(asset_map)}")

        # 4. SEED ASSIGNMENTS
        assignments_data = [
            {
                "asset_code": "LAP-001",
                "assigned_to_email": "employee2@dxasset.local",
                "assigned_by_email": "it_manager@dxasset.local",
                "assigned_date": datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc),
                "return_date": datetime(2026, 3, 1, 17, 0, tzinfo=timezone.utc),
                "status": AssignmentStatus.RETURNED,
                "notes": "Trả máy khi chuyển bộ phận công tác.",
            },
            {
                "asset_code": "LAP-001",
                "assigned_to_email": "employee1@dxasset.local",
                "assigned_by_email": "admin@dxasset.local",
                "assigned_date": datetime(2026, 3, 5, 8, 30, tzinfo=timezone.utc),
                "return_date": None,
                "status": AssignmentStatus.ACTIVE,
                "notes": "Bàn giao laptop chính thức cho nhân viên Sales.",
            },
            {
                "asset_code": "PC-001",
                "assigned_to_email": "employee2@dxasset.local",
                "assigned_by_email": "it_manager@dxasset.local",
                "assigned_date": datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc),
                "return_date": None,
                "status": AssignmentStatus.ACTIVE,
                "notes": "Bàn giao máy tính trạm làm việc cho phòng HR.",
            },
            {
                "asset_code": "MON-001",
                "assigned_to_email": "employee1@dxasset.local",
                "assigned_by_email": "it_manager@dxasset.local",
                "assigned_date": datetime(2026, 3, 5, 9, 0, tzinfo=timezone.utc),
                "return_date": None,
                "status": AssignmentStatus.ACTIVE,
                "notes": "Bàn giao màn hình Dell UltraSharp 27 inch.",
            },
        ]

        assignments_created = 0
        for asm in assignments_data:
            asset = asset_map[asm["asset_code"]]
            to_user = user_map[asm["assigned_to_email"]]
            by_user = user_map[asm["assigned_by_email"]]

            if asm["status"] == AssignmentStatus.ACTIVE:
                existing = db.query(AssetAssignment).filter(
                    AssetAssignment.asset_id == asset.id,
                    AssetAssignment.status == AssignmentStatus.ACTIVE,
                ).first()
            else:
                existing = db.query(AssetAssignment).filter(
                    AssetAssignment.asset_id == asset.id,
                    AssetAssignment.assigned_to_user_id == to_user.id,
                    AssetAssignment.status == asm["status"],
                ).first()

            if not existing:
                assignment = AssetAssignment(
                    asset_id=asset.id,
                    assigned_to_user_id=to_user.id,
                    assigned_by_user_id=by_user.id,
                    assigned_date=asm["assigned_date"],
                    return_date=asm["return_date"],
                    status=asm["status"],
                    notes=asm["notes"],
                )
                db.add(assignment)
                db.flush()
                assignments_created += 1

        logger.info(f"-> Asset Assignments: Đã tạo {assignments_created} mới.")

        # 5. SEED INCIDENTS
        incidents_data = [
            {
                "ticket_code": "INC-2026-001",
                "asset_code": "LAP-001",
                "reporter_email": "employee1@dxasset.local",
                "assigned_it_email": "it_manager@dxasset.local",
                "title": "Laptop bị giật lag và quạt kêu to",
                "description": "Máy dùng ứng dụng văn phòng bị treo nhẹ và quạt tản nhiệt phát tiếng kêu lạ.",
                "category": IncidentCategory.HARDWARE,
                "priority": IncidentPriority.MEDIUM,
                "status": IncidentStatus.IN_PROGRESS,
                "resolution_notes": None,
                "repair_cost": 0.00,
            },
            {
                "ticket_code": "INC-2026-002",
                "asset_code": "KB-001",
                "reporter_email": "employee2@dxasset.local",
                "assigned_it_email": "it_manager@dxasset.local",
                "title": "Bàn phím cơ hỏng phím Space",
                "description": "Phím Spacebar không phản hồi khi gõ văn bản.",
                "category": IncidentCategory.PHYSICAL_DAMAGE,
                "priority": IncidentPriority.LOW,
                "status": IncidentStatus.OPEN,
                "resolution_notes": None,
                "repair_cost": 0.00,
            },
            {
                "ticket_code": "INC-2026-003",
                "asset_code": "PC-001",
                "reporter_email": "employee2@dxasset.local",
                "assigned_it_email": "it_manager@dxasset.local",
                "title": "Lỗi kết nối Wi-Fi nội bộ",
                "description": "Máy trạm không bắt được sóng Wi-Fi tầng 2 sau khi cập nhật Windows.",
                "category": IncidentCategory.NETWORK,
                "priority": IncidentPriority.HIGH,
                "status": IncidentStatus.RESOLVED,
                "resolution_notes": "Cập nhật driver card mạng không dây và khởi động lại dịch vụ WLAN AutoConfig.",
                "repair_cost": 0.00,
            },
        ]

        incidents_created = 0
        for inc in incidents_data:
            existing = db.query(Incident).filter(Incident.ticket_code == inc["ticket_code"]).first()
            if not existing:
                asset = asset_map[inc["asset_code"]]
                reporter = user_map[inc["reporter_email"]]
                it_user = user_map[inc["assigned_it_email"]] if inc["assigned_it_email"] else None

                incident = Incident(
                    ticket_code=inc["ticket_code"],
                    asset_id=asset.id,
                    reporter_id=reporter.id,
                    assigned_it_id=it_user.id if it_user else None,
                    title=inc["title"],
                    description=inc["description"],
                    category=inc["category"],
                    priority=inc["priority"],
                    status=inc["status"],
                    resolution_notes=inc["resolution_notes"],
                    repair_cost=inc["repair_cost"],
                )
                db.add(incident)
                db.flush()
                incidents_created += 1

        logger.info(f"-> Incidents: Đã tạo {incidents_created} mới.")

        # 6. SEED TECHNICIAN SKILLS
        skills_data = [
            {"email": "it_manager@dxasset.local", "category": IncidentCategory.HARDWARE, "skill_level": 5},
            {"email": "it_manager@dxasset.local", "category": IncidentCategory.NETWORK, "skill_level": 5},
            {"email": "it_manager@dxasset.local", "category": IncidentCategory.SOFTWARE, "skill_level": 4},
            {"email": "it_manager@dxasset.local", "category": IncidentCategory.POWER, "skill_level": 3},
            {"email": "it_manager@dxasset.local", "category": IncidentCategory.PHYSICAL_DAMAGE, "skill_level": 4},
            {"email": "it_manager@dxasset.local", "category": IncidentCategory.OTHER, "skill_level": 3},
            {"email": "admin@dxasset.local", "category": IncidentCategory.SOFTWARE, "skill_level": 5},
            {"email": "admin@dxasset.local", "category": IncidentCategory.OTHER, "skill_level": 5},
            {"email": "admin@dxasset.local", "category": IncidentCategory.HARDWARE, "skill_level": 3},
            {"email": "admin@dxasset.local", "category": IncidentCategory.NETWORK, "skill_level": 3},
            {"email": "admin@dxasset.local", "category": IncidentCategory.POWER, "skill_level": 4},
            {"email": "admin@dxasset.local", "category": IncidentCategory.PHYSICAL_DAMAGE, "skill_level": 2},
        ]

        skills_created = 0
        for s in skills_data:
            user = user_map.get(s["email"])
            if user:
                existing = db.query(TechnicianSkill).filter(
                    TechnicianSkill.user_id == user.id,
                    TechnicianSkill.category == s["category"],
                ).first()
                if not existing:
                    ts = TechnicianSkill(
                        user_id=user.id,
                        category=s["category"],
                        skill_level=s["skill_level"],
                    )
                    db.add(ts)
                    db.flush()
                    skills_created += 1

        logger.info(f"-> Technician Skills: Đã tạo {skills_created} bản ghi kỹ năng mới.")

        db.commit()
        logger.info("==================================================")
        logger.info("HOÀN TẤT NẠP DỮ LIỆU MẪU THÀNH CÔNG (SUCCESS)")
        logger.info("==================================================")

    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi trong quá trình nạp dữ liệu mẫu: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
