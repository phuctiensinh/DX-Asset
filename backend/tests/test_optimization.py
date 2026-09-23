import pytest
from fastapi.testclient import TestClient

from app.models import Asset, AssetStatus, AssetAssignment, Incident, Maintenance, TechnicianSkill, User, UserRole
from app.core.security import create_access_token
from app.schemas.optimization import AllocationRequest, CapacityRequest, ReplacementSimulationRequest
from app.services.optimization import OptimizationService


def test_capacity_is_deterministic_and_exposes_assumptions():
    result = OptimizationService.simulate_capacity(CapacityRequest(
        current_sla_days=5, target_sla_days=3, expected_incidents=30,
        incidents_per_technician_per_day=2, current_technician_count=4,
    ))
    assert result.estimated_required_technicians == 5
    assert result.estimated_gap == 1
    assert any("scenario estimate" in warning.lower() for warning in result.warnings)


def test_capacity_rejects_zero_capacity():
    with pytest.raises(ValueError):
        CapacityRequest(current_sla_days=5, target_sla_days=3, expected_incidents=1,
                        incidents_per_technician_per_day=0)


def test_replacement_simulation_straight_line_and_rounding():
    result = OptimizationService.simulate_replacement(ReplacementSimulationRequest(
        quantity=2, unit_cost=1000, useful_life_years=4, simulation_horizon_years=5,
        residual_value_rate=0.1,
    ))
    assert result.total_initial_cost == 2000
    assert result.residual_value == 200
    assert result.annual_depreciation == 450
    assert [x.estimated_book_value for x in result.estimated_book_value_by_year] == [1550, 1100, 650, 200, 200]
    assert "not derived from asset acquisition records" in result.warnings[0]


def test_fixed_residual_yearly_depreciation_and_ending_book_value():
    result = OptimizationService.simulate_replacement(ReplacementSimulationRequest(
        quantity=111, unit_cost=10000, useful_life_years=2,
        simulation_horizon_years=2, residual_value=1000,
    ))
    assert result.total_initial_cost == 1_110_000
    assert result.annual_depreciation == 554_500
    assert [row.depreciation_expense for row in result.estimated_book_value_by_year] == [554_500, 554_500]
    assert [row.estimated_book_value for row in result.estimated_book_value_by_year] == [555_500, 1_000]


def test_residual_rate_yearly_depreciation_and_ending_book_value():
    result = OptimizationService.simulate_replacement(ReplacementSimulationRequest(
        quantity=111, unit_cost=10000, useful_life_years=2,
        simulation_horizon_years=2, residual_value_rate=0.1,
    ))
    assert result.total_initial_cost == 1_110_000
    assert result.residual_value == 111_000
    assert result.annual_depreciation == 499_500
    assert [row.depreciation_expense for row in result.estimated_book_value_by_year] == [499_500, 499_500]
    assert [row.estimated_book_value for row in result.estimated_book_value_by_year] == [610_500, 111_000]


def test_replacement_residual_validation():
    with pytest.raises(ValueError):
        ReplacementSimulationRequest(quantity=1, unit_cost=100, useful_life_years=2,
                                     simulation_horizon_years=2, residual_value=101)


def test_allocation_only_counts_in_stock_and_does_not_mutate(db):
    department = db.query(Asset).first().department_id
    category = "PHASE14_TEST"
    available = Asset(asset_code="P14-STOCK", name="Stock candidate", category=category,
                      status=AssetStatus.IN_STOCK, department_id=department)
    assigned = Asset(asset_code="P14-ASSIGNED", name="Assigned asset", category=category,
                     status=AssetStatus.ASSIGNED, department_id=department)
    db.add_all([available, assigned]); db.commit()
    before = (available.status, assigned.status, available.current_user_id, assigned.current_user_id)
    result = OptimizationService.simulate_allocation(db, AllocationRequest(
        department_id=department, asset_category=category, requested_quantity=2))
    assert result.available_quantity == 1
    assert result.shortage_quantity == 1
    assert not result.enough
    db.refresh(available); db.refresh(assigned)
    assert before == (available.status, assigned.status, available.current_user_id, assigned.current_user_id)
    db.delete(available); db.delete(assigned); db.commit()


def test_optimization_rbac(client: TestClient, db, employee_token: str, admin_token: str):
    headers = {"Authorization": f"Bearer {employee_token}"}
    payload = {"current_sla_days": 5, "target_sla_days": 3, "expected_incidents": 10,
               "incidents_per_technician_per_day": 1}
    assert client.post("/api/v1/optimization/what-if/capacity", json=payload, headers=headers).status_code == 403
    admin = client.post("/api/v1/optimization/what-if/capacity", json=payload,
                        headers={"Authorization": f"Bearer {admin_token}"})
    assert admin.status_code == 200
    for role in (UserRole.IT_ASSET_MANAGER, UserRole.MANAGER):
        user = db.query(User).filter(User.role == role).first()
        if user:
            token = create_access_token(subject=user.id, extra_claims={"email": user.email, "role": str(user.role)})
            response = client.post("/api/v1/optimization/what-if/capacity", json=payload,
                                   headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200


def test_assistant_denies_employee_global_analytics(client: TestClient, employee_token: str):
    response = client.post("/api/v1/assistant/chat", json={"message": "Tài sản nào nên ưu tiên thay thế?"},
                           headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 403


def test_assistant_employee_scope_returns_owned_assets(client: TestClient, employee_token: str):
    response = client.post("/api/v1/assistant/chat", json={"message": "Danh sách tài sản của tôi"},
                           headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 200
    assert response.json()["intent"] == "MY_ASSIGNED_ASSETS"


def test_assistant_phase14_intents(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    allocation = client.post("/api/v1/assistant/chat", json={"message": "Phòng IT còn đủ laptop để cấp cho 5 người không?"}, headers=headers)
    assert allocation.status_code == 200
    assert allocation.json()["intent"] == "ALLOCATION_SIMULATION"
    capacity = client.post("/api/v1/assistant/chat", json={"message": "Nếu SLA từ 5 xuống 3 ngày với 30 incident, năng lực 2 mỗi ngày mỗi IT"}, headers=headers)
    assert capacity.json()["intent"] == "CAPACITY_SIMULATION"
    depreciation = client.post("/api/v1/assistant/chat", json={"message": "10 laptop giá 15 triệu mỗi chiếc dùng 3 năm khấu hao"}, headers=headers)
    assert depreciation.json()["intent"] == "REPLACEMENT_SIMULATION"
    priority = client.post("/api/v1/assistant/chat", json={"message": "Tài sản nào nên ưu tiên thay thế?"}, headers=headers)
    assert priority.json()["intent"] == "REPLACEMENT_PRIORITY"


def test_simulations_do_not_mutate_business_records(db):
    from app.models.department import Department
    model_counts = [db.query(model).count() for model in (Asset, AssetAssignment, Incident, Maintenance, User, TechnicianSkill)]
    OptimizationService.simulate_capacity(CapacityRequest(
        current_sla_days=5, target_sla_days=3, expected_incidents=12, incidents_per_technician_per_day=2))
    OptimizationService.simulate_replacement(ReplacementSimulationRequest(
        quantity=10, unit_cost=1000, useful_life_years=3, simulation_horizon_years=3))
    department_id = db.query(Department.id).first()[0]
    OptimizationService.simulate_allocation(db, AllocationRequest(
        department_id=department_id, asset_category="no-such-category", requested_quantity=1))
    assert model_counts == [db.query(model).count() for model in (Asset, AssetAssignment, Incident, Maintenance, User, TechnicianSkill)]
