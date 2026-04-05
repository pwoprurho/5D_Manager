from datetime import datetime
from enum import Enum
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    staff = "staff"
    manager = "manager"
    director = "director"
    admin = "admin"
    president = "president"

class StatusEnum(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"        # Staff completed task
    inspected = "inspected"        # Manager verified
    approved = "approved"          # Director final approval
    blocked = "blocked"
    critical = "critical"

class MaterialRequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    issued = "issued"
    rejected = "rejected"

class WPType(str, Enum):
    task = "task"
    bug = "bug"
    milestone = "milestone"
    phase = "phase"

class WPPriority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"
    immediate = "immediate"

class Design(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    model_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Project(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    design_id: Optional[int] = None
    bim_model_url: Optional[str] = None # Legacy support
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkPackage(BaseModel):
    id: Optional[int] = None
    project_id: int
    bim_element_id: Optional[str] = None
    name: str
    status: StatusEnum = StatusEnum.not_started
    progress_pct: int = 0
    budget_amount: Decimal = Decimal("0")
    actual_cost: Decimal = Decimal("0")
    
    verified_by_id: Optional[str] = None  # UUID for Supabase Auth
    approved_by_id: Optional[str] = None  # UUID for Supabase Auth
    assignee_id: Optional[str] = None     # Assignee tracking for OpenProject workflow
    
    type: WPType = WPType.task
    priority: WPPriority = WPPriority.normal
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    parent_id: Optional[int] = None
    
    estimated_hours: Decimal = Decimal("0")
    spent_hours: Decimal = Decimal("0")


class SiteUpdate(BaseModel):
    id: Optional[int] = None
    work_package_id: int
    submitted_by_id: str  # UUID for Supabase Auth
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_long: Optional[float] = None
    weather_info: Optional[str] = None
    materials_used: Optional[str] = None
    cost_incurred: Decimal = Decimal("0")


class User(BaseModel):
    id: str  # This is the UUID from Supabase Auth
    username: str
    email: str
    role: UserRole = UserRole.staff
    is_active: bool = True


class Material(BaseModel):
    id: Optional[int] = None
    name: str
    unit: str
    current_stock: float = 0
    unit_cost: Decimal = Decimal("0")
    low_stock_threshold: float = 10.0


class MaterialRequest(BaseModel):
    id: Optional[int] = None
    project_id: int
    work_package_id: Optional[int] = None
    requester_id: Optional[str] = None  # UUID (set by backend)
    material_id: int
    quantity_requested: float
    status: MaterialRequestStatus = MaterialRequestStatus.pending
    request_date: datetime = Field(default_factory=datetime.utcnow)


class MaterialUsage(BaseModel):
    id: Optional[int] = None
    project_id: int
    work_package_id: Optional[int] = None
    material_id: int
    quantity_used: float
    usage_date: datetime = Field(default_factory=datetime.utcnow)


class ProjectAssignment(BaseModel):
    id: Optional[int] = None
    project_id: int
    user_id: str  # UUID
    assigned_role: str = "member"
    assigned_at: datetime = Field(default_factory=datetime.utcnow)

