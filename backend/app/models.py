from datetime import datetime
from enum import Enum
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    engineer = "engineer"
    manager = "manager"
    director = "director"
    admin = "admin"

class StatusEnum(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"        # Engineer completed task
    inspected = "inspected"        # Manager verified
    approved = "approved"          # Director final approval
    blocked = "blocked"
    critical = "critical"

class MemoStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

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

class LoggingPeriod(str, Enum):
    daily = "daily"
    weekly = "weekly"
    bi_weekly = "bi_weekly"
    monthly = "monthly"
    periodic = "periodic"

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
    bim_model_url: Optional[str] = None # Primary Project Resource (Replaced Blueprints)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Stage(BaseModel):
    id: Optional[int] = None
    project_id: int
    name: str
    status: StatusEnum = StatusEnum.not_started
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkPackage(BaseModel):
    id: Optional[int] = None
    project_id: int
    stage_id: Optional[int] = None # Linked to structural stage
    bim_element_id: Optional[str] = None
    name: str
    status: StatusEnum = StatusEnum.not_started
    progress_pct: int = Field(default=0, ge=0, le=100)
    budget_amount: Decimal = Field(default=Decimal("0"), ge=0)
    actual_cost: Decimal = Field(default=Decimal("0"), ge=0)
    
    verified_by_id: Optional[str] = None  # UUID for Supabase Auth
    approved_by_id: Optional[str] = None  # UUID for Supabase Auth
    assignee_id: Optional[str] = None     # Assignee tracking for OpenProject workflow
    
    type: WPType = WPType.task
    priority: WPPriority = WPPriority.normal
    logging_period: LoggingPeriod = LoggingPeriod.daily
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
    cost_incurred: Decimal = Field(default=Decimal("0"), ge=0)
    progress_captured: int = Field(default=0, ge=0, le=100) # Added to track historical progress snapshoat


class User(BaseModel):
    id: str  # This is the UUID from Supabase Auth
    username: str
    email: str
    role: UserRole = UserRole.engineer
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


class ProjectInventory(BaseModel):
    id: Optional[int] = None
    project_id: int
    material_id: int
    quantity: float = 0
    unit_cost: Decimal = Decimal("0")
    low_stock_threshold: float = 10.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectAssignment(BaseModel):
    id: Optional[int] = None
    project_id: int
    user_id: str  # UUID
    assigned_role: str = "member"
    assigned_at: datetime = Field(default_factory=datetime.utcnow)

class InternalMemo(BaseModel):
    id: Optional[int] = None
    project_id: int
    work_package_id: int
    requested_by_id: str  # User UUID
    requested_progress_pct: Optional[int] = None
    requested_status: Optional[str] = None
    subject: str
    content: str
    status: MemoStatus = MemoStatus.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_by_id: Optional[str] = None # Director UUID

class MemoCreate(BaseModel):
    work_package_id: int
    requested_progress_pct: Optional[int] = None
    requested_status: Optional[str] = None
    subject: str
    content: str

class AuditAction(str, Enum):
    promotion = "promotion"
    deactivation = "deactivation"
    activation = "activation"
    profile_update = "profile_update"
    enrollment = "enrollment"

class AuditLog(BaseModel):
    id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    actor_id: str  # User who performed the action
    target_id: str # User affected by the action
    action: AuditAction
    details: Optional[dict] = None
