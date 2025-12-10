from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, SQLModel, create_engine, Session, Relationship, select, or_
from typing import Optional, List
from datetime import datetime, date, timedelta
from enum import Enum
import csv
import io
from typing import Optional, List
from datetime import datetime, date, timedelta
from enum import Enum
import csv
import io

# ============================================
# Database Setup
# ============================================
DATABASE_URL = "sqlite:///./asset_manager.db"
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


# ============================================
# Enums
# ============================================
class AssetStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    IN_MAINTENANCE = "In Maintenance"
    RETIRED = "Retired"


class AssetState(str, Enum):
    GOOD = "Good"
    BAD = "Bad"
    UGLY = "Ugly"


class WorkOrderStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class WorkOrderPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class PMFrequencyUnit(str, Enum):
    DAYS = "Days"
    HOURS = "Hours"
    MONTHS = "Months"


class InventoryStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


class InventoryState(str, Enum):
    ACTIVE = "Active"
    INACTIVE_SCRAP = "In-Active & Scrap"
    NOT_IN_USE_TO_BE_SCRAPPED = "Not in Use - To be Scrapped"
    IN_USE = "In Use"


# ============================================
# Models - Vendor
# ============================================
class Vendor(SQLModel, table=True):
    __tablename__ = "vendors"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    assets: List["Asset"] = Relationship(back_populates="vendor_rel")


# ============================================
# Models - Location
# ============================================
class Location(SQLModel, table=True):
    __tablename__ = "locations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    parent_id: Optional[int] = Field(default=None, foreign_key="locations.id")
    
    # Relationships
    assets: List["Asset"] = Relationship(
        back_populates="location_rel",
        sa_relationship_kwargs={"foreign_keys": "Asset.location_id"}
    )
    

# ============================================
# Models - Asset Registry
# ============================================
class Asset(SQLModel, table=True):
    __tablename__ = "assets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: str = Field(unique=True, index=True)  # Custom Asset ID
    name: str = Field(index=True)
    category: str = Field(index=True)
    status: AssetStatus = Field(default=AssetStatus.ACTIVE)
    
    # Parent-Child Relationship for Sub-Assets
    parent_asset_id: Optional[int] = Field(default=None, foreign_key="assets.id")
    
    # Location & Ownership
    location_id: Optional[int] = Field(default=None, foreign_key="locations.id")
    station_id: Optional[int] = Field(default=None, foreign_key="locations.id")
    owner_cost_center: Optional[str] = None
    
    # Vendor & Identification
    vendor_name: Optional[str] = None  # Legacy field - vendor name as string
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendors.id")
    serial_number: Optional[str] = Field(default=None, unique=True)
    tag_id: Optional[str] = Field(default=None, unique=True)
    sap_id: Optional[str] = None  # SAP identifier (numbers only)
    
    # Purchase & Warranty
    purchase_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    warranty_date: Optional[date] = None
    purchase_cost: Optional[float] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    capitalised_on: Optional[date] = None
    
    # Organization
    company_code: Optional[str] = Field(default="IN07")
    plant_code: Optional[str] = Field(default="IN08")
    currency: Optional[str] = Field(default="INR")
    location_name: Optional[str] = Field(default="Plant - Bangalore")  # Renamed to avoid conflict
    state: Optional[AssetState] = None
    
    # Tracking
    meter_reading: Optional[float] = None  # For runtime-based PM
    notes: Optional[str] = None
    physically_verified: bool = Field(default=False)  # Computed field for verification status
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    location_rel: Optional[Location] = Relationship(
        back_populates="assets",
        sa_relationship_kwargs={"foreign_keys": "[Asset.location_id]"}
    )
    vendor_rel: Optional[Vendor] = Relationship(back_populates="assets")
    work_orders: List["WorkOrderAsset"] = Relationship(back_populates="asset")
    pm_templates: List["PMTemplate"] = Relationship(back_populates="asset")
    spare_parts: List["AssetSparePart"] = Relationship(back_populates="asset")

    #---------------- Removed duplicate invoice fields ----------------#
    

# ============================================
# Models - Work Orders
# ============================================
class WorkOrderAsset(SQLModel, table=True):
    __tablename__ = "work_order_assets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    work_order_id: int = Field(foreign_key="work_orders.id")
    asset_id: int = Field(foreign_key="assets.id")
    
    # Relationships
    work_order: "WorkOrder" = Relationship(back_populates="asset_links")
    asset: Asset = Relationship(back_populates="work_orders")


class WorkOrder(SQLModel, table=True):
    __tablename__ = "work_orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    wo_number: str = Field(unique=True, index=True)
    summary: str
    description: Optional[str] = None
    
    # Priority & Status
    priority: WorkOrderPriority = Field(default=WorkOrderPriority.MEDIUM)
    status: WorkOrderStatus = Field(default=WorkOrderStatus.OPEN)
    
    # Assignment & Scheduling
    technician: Optional[str] = None
    due_date: Optional[datetime] = None
    
    # Time Tracking
    time_spent_hours: Optional[float] = Field(default=0)
    completion_notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # PM Link
    pm_template_id: Optional[int] = Field(default=None, foreign_key="pm_templates.id")
    
    # Relationships
    asset_links: List[WorkOrderAsset] = Relationship(back_populates="work_order")
    parts_used: List["WorkOrderPart"] = Relationship(back_populates="work_order")
    pm_template: Optional["PMTemplate"] = Relationship(back_populates="generated_work_orders")


# ============================================
# Models - Preventive Maintenance
# ============================================
class PMTemplate(SQLModel, table=True):
    __tablename__ = "pm_templates"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    
    # Frequency Configuration
    frequency_value: int  # e.g., 90 for "every 90 days"
    frequency_unit: PMFrequencyUnit = Field(default=PMFrequencyUnit.DAYS)
    
    # Asset Link
    asset_id: int = Field(foreign_key="assets.id")
    
    # Tracking
    last_generated_date: Optional[datetime] = None
    next_due_date: Optional[datetime] = None
    is_active: bool = Field(default=True)
    
    # Work Order Template
    wo_summary_template: str
    wo_description_template: Optional[str] = None
    default_priority: WorkOrderPriority = Field(default=WorkOrderPriority.MEDIUM)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    asset: Asset = Relationship(back_populates="pm_templates")
    generated_work_orders: List[WorkOrder] = Relationship(back_populates="pm_template")


# ============================================
# Models - Spare Parts
# ============================================
class InventoryItem(SQLModel, table=True):
    __tablename__ = "inventory_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    item_name: str = Field(index=True)
    part_number: str = Field(unique=True, index=True)
    description: Optional[str] = None
    
    # Stock Levels
    stock_on_hand: int = Field(default=0)
    min_stock: int = Field(default=0)
    max_stock: int = Field(default=100)
    
    # Costing & Financial
    unit_cost: Optional[float] = None
    book_value: Optional[float] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    capitalised_on: Optional[date] = None
    
    # Organization
    company_code: Optional[str] = Field(default="IN06")
    plant_code: Optional[str] = Field(default="IN08")
    currency: Optional[str] = Field(default="INR")
    cost_center: Optional[str] = None
    
    # Location & Vendor
    location_id: Optional[int] = Field(default=None, foreign_key="locations.id")
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendors.id")
    
    # Status & State
    status: InventoryStatus = Field(default=InventoryStatus.ACTIVE)
    state: Optional[InventoryState] = None
    remarks: Optional[str] = None
    
    # Tracking
    physically_verified: bool = Field(default=False)  # Computed field for verification status
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    location_rel: Optional[Location] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[InventoryItem.location_id]"}
    )
    vendor_rel: Optional[Vendor] = Relationship()
    work_order_usage: List["WorkOrderPart"] = Relationship(back_populates="inventory_item")
    asset_usage: List["AssetSparePart"] = Relationship(back_populates="inventory_item")


class WorkOrderPart(SQLModel, table=True):
    __tablename__ = "work_order_parts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    work_order_id: int = Field(foreign_key="work_orders.id")
    inventory_item_id: int = Field(foreign_key="inventory_items.id")
    quantity_used: int
    
    # Relationships
    work_order: WorkOrder = Relationship(back_populates="parts_used")
    inventory_item: InventoryItem = Relationship(back_populates="work_order_usage")


# ============================================
# Models - Asset Spare Parts
# ============================================
class AssetSparePart(SQLModel, table=True):
    __tablename__ = "asset_spare_parts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="assets.id")
    inventory_item_id: int = Field(foreign_key="inventory_items.id")
    quantity: int = Field(default=1)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    asset: Asset = Relationship(back_populates="spare_parts")
    inventory_item: InventoryItem = Relationship(back_populates="asset_usage")


# Request/Response models for Asset Spare Parts
class AssetSparePartCreate(SQLModel):
    inventory_item_id: int
    quantity: int = 1
    notes: Optional[str] = None


class AssetSparePartUpdate(SQLModel):
    quantity: Optional[int] = None
    notes: Optional[str] = None


# ============================================
# Models - Physical Verification
# ============================================
class PhysicalVerification(SQLModel, table=True):
    __tablename__ = "physical_verification"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Verification Status
    phy_ver_status: bool = Field(default=False)  # Default as No (False)
    phy_ver_date: Optional[datetime] = None
    
    # Asset Information
    new_tag: Optional[str] = None
    physical_location_id: Optional[int] = Field(default=None, foreign_key="locations.id")
    condition_of_asset: Optional[str] = None
    
    # Verification Details
    verification_done_by: Optional[str] = None
    next_pv_planned_date: Optional[date] = None
    comments: Optional[str] = None
    
    # Links
    asset_id: Optional[int] = Field(default=None, foreign_key="assets.id")
    spare_part_id: Optional[int] = Field(default=None, foreign_key="inventory_items.id")
    
    # Tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    physical_location_rel: Optional[Location] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[PhysicalVerification.physical_location_id]"}
    )
    asset_rel: Optional[Asset] = Relationship()
    spare_part_rel: Optional[InventoryItem] = Relationship()


# ============================================
# FastAPI App
# ============================================
app = FastAPI(title="Asset Manager API", version="1.0.0")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def read_root():
    return {"message": "Asset Manager API", "version": "1.0.0"}


# ============================================
# LOCATION ENDPOINTS
# ============================================
@app.post("/locations", response_model=Location)
def create_location(location: Location, session: Session = Depends(get_session)):
    session.add(location)
    session.commit()
    session.refresh(location)
    return location


@app.get("/locations", response_model=List[Location])
def get_locations(session: Session = Depends(get_session)):
    locations = session.exec(select(Location)).all()
    return locations


# ============================================
# VENDOR ENDPOINTS
# ============================================
@app.post("/vendors", response_model=Vendor)
def create_vendor(vendor: Vendor, session: Session = Depends(get_session)):
    # Convert date strings to Python datetime objects
    vendor = convert_vendor_dates(vendor)
    
    # Ensure datetime fields are datetime objects
    vendor.created_at = datetime.utcnow()
    vendor.updated_at = datetime.utcnow()
    session.add(vendor)
    
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        # Handle specific constraint violations
        if "UNIQUE constraint failed:" in str(e):
            raise HTTPException(status_code=400, detail=f"A vendor with this information already exists. Please check for duplicates.")
        else:
            # Re-raise other errors
            raise HTTPException(status_code=400, detail=f"Error creating vendor: {str(e)}")
    
    session.refresh(vendor)
    return vendor


@app.get("/vendors", response_model=List[Vendor])
def get_vendors(session: Session = Depends(get_session)):
    vendors = session.exec(select(Vendor)).all()
    return vendors


@app.get("/vendors/{vendor_id}", response_model=Vendor)
def get_vendor(vendor_id: int, session: Session = Depends(get_session)):
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@app.put("/vendors/{vendor_id}", response_model=Vendor)
def update_vendor(vendor_id: int, vendor_update: Vendor, session: Session = Depends(get_session)):
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Convert date strings to Python datetime objects
    vendor_update = convert_vendor_dates(vendor_update)
    
    vendor_data = vendor_update.dict(exclude_unset=True)
    for key, value in vendor_data.items():
        if key not in ['created_at'] and hasattr(vendor, key):
            setattr(vendor, key, value)
    
    vendor.updated_at = datetime.utcnow()
    session.add(vendor)
    
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        # Handle specific constraint violations
        if "UNIQUE constraint failed:" in str(e):
            raise HTTPException(status_code=400, detail=f"A vendor with this information already exists. Please check for duplicates.")
        else:
            # Re-raise other errors
            raise HTTPException(status_code=400, detail=f"Error updating vendor: {str(e)}")
    
    session.refresh(vendor)
    return vendor


@app.delete("/vendors/{vendor_id}")
def delete_vendor(vendor_id: int, session: Session = Depends(get_session)):
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    session.delete(vendor)
    session.commit()
    return {"message": "Vendor deleted successfully"}


# ============================================
# Helper Functions
# ============================================

def parse_date_string(date_string: str | None) -> date | None:
    """Convert date string to Python date object"""
    if not date_string:
        return None
    if isinstance(date_string, date):
        return date_string  # Already a date object
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def parse_datetime_string(datetime_string: str | None) -> datetime | None:
    """Convert datetime string to Python datetime object"""
    if not datetime_string:
        return None
    if isinstance(datetime_string, datetime):
        return datetime_string  # Already a datetime object
    try:
        # Handle ISO format with or without milliseconds/timezone
        if 'T' in datetime_string:
            # ISO format: 2025-12-10T10:30:00 or 2025-12-10T10:30:00.123Z
            datetime_string = datetime_string.replace('Z', '').split('.')[0]
            return datetime.fromisoformat(datetime_string)
        else:
            # Just date format: 2025-12-10
            return datetime.strptime(datetime_string, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def convert_asset_dates(asset: Asset) -> Asset:
    """Convert string dates to Python date objects in an Asset"""
    if asset.purchase_date and isinstance(asset.purchase_date, str):
        asset.purchase_date = parse_date_string(asset.purchase_date)
    if asset.warranty_expiry and isinstance(asset.warranty_expiry, str):
        asset.warranty_expiry = parse_date_string(asset.warranty_expiry)
    if asset.warranty_date and isinstance(asset.warranty_date, str):
        asset.warranty_date = parse_date_string(asset.warranty_date)
    if asset.invoice_date and isinstance(asset.invoice_date, str):
        asset.invoice_date = parse_date_string(asset.invoice_date)
    if asset.capitalised_on and isinstance(asset.capitalised_on, str):
        asset.capitalised_on = parse_date_string(asset.capitalised_on)
    return asset


def convert_vendor_dates(vendor: Vendor) -> Vendor:
    """Convert string datetimes to Python datetime objects in a Vendor"""
    if vendor.created_at and isinstance(vendor.created_at, str):
        vendor.created_at = parse_datetime_string(vendor.created_at)
    if vendor.updated_at and isinstance(vendor.updated_at, str):
        vendor.updated_at = parse_datetime_string(vendor.updated_at)
    return vendor


def convert_work_order_dates(work_order: WorkOrder) -> WorkOrder:
    """Convert string datetimes to Python datetime objects in a WorkOrder"""
    if work_order.due_date and isinstance(work_order.due_date, str):
        work_order.due_date = parse_datetime_string(work_order.due_date)
    if work_order.created_at and isinstance(work_order.created_at, str):
        work_order.created_at = parse_datetime_string(work_order.created_at)
    if work_order.started_at and isinstance(work_order.started_at, str):
        work_order.started_at = parse_datetime_string(work_order.started_at)
    if work_order.completed_at and isinstance(work_order.completed_at, str):
        work_order.completed_at = parse_datetime_string(work_order.completed_at)
    return work_order


def convert_pm_template_dates(pm_template: PMTemplate) -> PMTemplate:
    """Convert string datetimes to Python datetime objects in a PMTemplate"""
    if pm_template.last_generated_date and isinstance(pm_template.last_generated_date, str):
        pm_template.last_generated_date = parse_datetime_string(pm_template.last_generated_date)
    if pm_template.next_due_date and isinstance(pm_template.next_due_date, str):
        pm_template.next_due_date = parse_datetime_string(pm_template.next_due_date)
    if pm_template.created_at and isinstance(pm_template.created_at, str):
        pm_template.created_at = parse_datetime_string(pm_template.created_at)
    return pm_template


def convert_inventory_item_dates(item: InventoryItem) -> InventoryItem:
    """Convert string datetimes to Python datetime objects in an InventoryItem"""
    if item.created_at and isinstance(item.created_at, str):
        item.created_at = parse_datetime_string(item.created_at)
    if item.updated_at and isinstance(item.updated_at, str):
        item.updated_at = parse_datetime_string(item.updated_at)
    return item


def convert_physical_verification_dates(verification: PhysicalVerification) -> PhysicalVerification:
    """Convert string dates/datetimes to Python date/datetime objects in a PhysicalVerification"""
    if verification.phy_ver_date and isinstance(verification.phy_ver_date, str):
        verification.phy_ver_date = parse_datetime_string(verification.phy_ver_date)
    if verification.next_pv_planned_date and isinstance(verification.next_pv_planned_date, str):
        verification.next_pv_planned_date = parse_date_string(verification.next_pv_planned_date)
    if verification.created_at and isinstance(verification.created_at, str):
        verification.created_at = parse_datetime_string(verification.created_at)
    if verification.updated_at and isinstance(verification.updated_at, str):
        verification.updated_at = parse_datetime_string(verification.updated_at)
    return verification


def compute_asset_verification_status(asset_id: int, session: Session) -> bool:
    """
    Compute whether an asset is currently physically verified based on verification records.
    
    Logic:
    1. If no verification records exist, return False
    2. Get the latest verification record (by phy_ver_date)
    3. If the latest record has phy_ver_status = False, return False
    4. If the latest record has phy_ver_status = True:
       - If next_pv_planned_date is None, return True (verified indefinitely)
       - If current date is past next_pv_planned_date, return False (verification expired)
       - Otherwise, return True (currently verified)
    """
    from datetime import date as date_type
    
    # Get all verification records for this asset, ordered by verification date descending
    statement = select(PhysicalVerification).where(
        PhysicalVerification.asset_id == asset_id
    ).order_by(PhysicalVerification.phy_ver_date.desc())
    
    verifications = session.exec(statement).all()
    
    # No verification records exist
    if not verifications:
        return False
    
    # Get the latest verification record
    latest_verification = verifications[0]
    
    # If not verified in the latest record
    if not latest_verification.phy_ver_status:
        return False
    
    # If verified but no next planned date, consider it verified
    if not latest_verification.next_pv_planned_date:
        return True
    
    # Check if current date is past the next verification date
    current_date = date_type.today()
    if current_date > latest_verification.next_pv_planned_date:
        return False  # Verification expired
    
    # Currently verified and not expired
    return True


def compute_spare_part_verification_status(spare_part_id: int, session: Session) -> bool:
    """
    Compute whether a spare part is currently physically verified based on verification records.
    
    Logic: Same as asset verification
    1. If no verification records exist, return False
    2. Get the latest verification record (by phy_ver_date)
    3. If the latest record has phy_ver_status = False, return False
    4. If the latest record has phy_ver_status = True:
       - If next_pv_planned_date is None, return True (verified indefinitely)
       - If current date is past next_pv_planned_date, return False (verification expired)
       - Otherwise, return True (currently verified)
    """
    from datetime import date as date_type
    
    # Get all verification records for this spare part, ordered by verification date descending
    statement = select(PhysicalVerification).where(
        PhysicalVerification.spare_part_id == spare_part_id
    ).order_by(PhysicalVerification.phy_ver_date.desc())
    
    verifications = session.exec(statement).all()
    
    # No verification records exist
    if not verifications:
        return False
    
    # Get the latest verification record
    latest_verification = verifications[0]
    
    # If not verified in the latest record
    if not latest_verification.phy_ver_status:
        return False
    
    # If verified but no next planned date, consider it verified
    if not latest_verification.next_pv_planned_date:
        return True
    
    # Check if current date is past the next verification date
    current_date = date_type.today()
    if current_date > latest_verification.next_pv_planned_date:
        return False  # Verification expired
    
    # Currently verified and not expired
    return True


# ============================================
# ASSET REGISTRY ENDPOINTS
# ============================================
@app.post("/assets", response_model=Asset)
def create_asset(asset: Asset, session: Session = Depends(get_session)):
    # Convert date strings to Python date objects
    asset = convert_asset_dates(asset)
    
    # Ensure datetime fields are datetime objects
    asset.created_at = datetime.utcnow()
    asset.updated_at = datetime.utcnow()
    session.add(asset)
    
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        # Handle specific constraint violations
        if "UNIQUE constraint failed: assets.asset_id" in str(e):
            raise HTTPException(status_code=400, detail=f"Asset ID '{asset.asset_id}' already exists. Please use a unique Asset ID.")
        elif "UNIQUE constraint failed: assets.serial_number" in str(e):
            raise HTTPException(status_code=400, detail=f"Serial number '{asset.serial_number}' already exists. Please use a unique serial number.")
        elif "UNIQUE constraint failed: assets.tag_id" in str(e):
            raise HTTPException(status_code=400, detail=f"Tag ID '{asset.tag_id}' already exists. Please use a unique tag ID.")
        else:
            # Re-raise other errors
            raise HTTPException(status_code=400, detail=f"Error creating asset: {str(e)}")
    
    session.refresh(asset)
    return asset


@app.get("/assets", response_model=List[Asset])
def get_assets(
    status: Optional[AssetStatus] = None,
    category: Optional[str] = None,
    location_id: Optional[int] = None,
    search: Optional[str] = None,
    session: Session = Depends(get_session)
):
    query = select(Asset)
    
    if status:
        query = query.where(Asset.status == status)
    if category:
        query = query.where(Asset.category == category)
    if location_id:
        query = query.where(Asset.location_id == location_id)
    if search:
        query = query.where(
            or_(
                Asset.name.contains(search),
                Asset.asset_id.contains(search),
                Asset.serial_number.contains(search)
            )
        )
    
    assets = session.exec(query).all()
    
    # Compute verification status for each asset
    for asset in assets:
        if asset.id:
            asset.physically_verified = compute_asset_verification_status(asset.id, session)
    
    return assets


@app.get("/assets/{asset_id}", response_model=Asset)
def get_asset(asset_id: int, session: Session = Depends(get_session)):
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Compute verification status
    if asset.id:
        asset.physically_verified = compute_asset_verification_status(asset.id, session)
    
    return asset


@app.put("/assets/{asset_id}", response_model=Asset)
def update_asset(asset_id: int, asset_update: Asset, session: Session = Depends(get_session)):
    db_asset = session.get(Asset, asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Convert date strings to Python date objects
    asset_update = convert_asset_dates(asset_update)
    
    # Get update data - use dict() to include None values for clearing fields
    asset_data = asset_update.dict(exclude_unset=True, exclude_none=False)
    asset_data["updated_at"] = datetime.utcnow()
    
    # Update asset fields
    for key, value in asset_data.items():
        if key not in ['created_at'] and hasattr(db_asset, key):
            # Explicitly allow None for optional fields like parent_asset_id
            setattr(db_asset, key, value)
    
    session.add(db_asset)
    
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        # Handle specific constraint violations
        if "UNIQUE constraint failed: assets.asset_id" in str(e):
            raise HTTPException(status_code=400, detail=f"Asset ID '{db_asset.asset_id}' already exists. Please use a unique Asset ID.")
        elif "UNIQUE constraint failed: assets.serial_number" in str(e):
            raise HTTPException(status_code=400, detail=f"Serial number '{db_asset.serial_number}' already exists. Please use a unique serial number.")
        elif "UNIQUE constraint failed: assets.tag_id" in str(e):
            raise HTTPException(status_code=400, detail=f"Tag ID '{db_asset.tag_id}' already exists. Please use a unique tag ID.")
        else:
            # Re-raise other errors
            raise HTTPException(status_code=400, detail=f"Error updating asset: {str(e)}")
    
    session.refresh(db_asset)
    return db_asset


@app.patch("/assets/{asset_id}/retire")
def retire_asset(asset_id: int, session: Session = Depends(get_session)):
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    asset.status = AssetStatus.RETIRED
    asset.updated_at = datetime.utcnow()
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


@app.get("/assets/{asset_id}/sub-assets", response_model=List[Asset])
def get_sub_assets(asset_id: int, session: Session = Depends(get_session)):
    """Get all sub-assets (children) of a parent asset"""
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get all assets where parent_asset_id equals the given asset_id
    sub_assets = session.exec(
        select(Asset).where(Asset.parent_asset_id == asset_id)
    ).all()
    
    # Compute verification status for each sub-asset
    for sub_asset in sub_assets:
        if sub_asset.id:
            sub_asset.physically_verified = compute_asset_verification_status(sub_asset.id, session)
    
    return sub_assets


# ============================================
# ASSET SPARE PARTS ENDPOINTS
# ============================================
@app.get("/assets/{asset_id}/spare-parts")
def get_asset_spare_parts(asset_id: int, session: Session = Depends(get_session)):
    """Get all spare parts associated with an asset"""
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    spare_parts = session.exec(
        select(AssetSparePart).where(AssetSparePart.asset_id == asset_id)
    ).all()
    
    # Enrich with inventory item details
    result = []
    for sp in spare_parts:
        item = session.get(InventoryItem, sp.inventory_item_id)
        if item:
            result.append({
                "id": sp.id,
                "asset_id": sp.asset_id,
                "inventory_item_id": sp.inventory_item_id,
                "quantity": sp.quantity,
                "notes": sp.notes,
                "created_at": sp.created_at,
                "item_name": item.item_name,
                "part_number": item.part_number,
                "unit_cost": item.unit_cost,
                "stock_on_hand": item.stock_on_hand
            })
    
    return result


@app.post("/assets/{asset_id}/spare-parts")
def add_spare_part_to_asset(
    asset_id: int,
    spare_part_data: AssetSparePartCreate,
    session: Session = Depends(get_session)
):
    """Add a spare part to an asset"""
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    item = session.get(InventoryItem, spare_part_data.inventory_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Spare part not found")
    
    # Check if already exists
    existing = session.exec(
        select(AssetSparePart).where(
            AssetSparePart.asset_id == asset_id,
            AssetSparePart.inventory_item_id == spare_part_data.inventory_item_id
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="This spare part is already associated with this asset")
    
    spare_part = AssetSparePart(
        asset_id=asset_id,
        inventory_item_id=spare_part_data.inventory_item_id,
        quantity=spare_part_data.quantity,
        notes=spare_part_data.notes
    )
    
    session.add(spare_part)
    session.commit()
    session.refresh(spare_part)
    
    return {
        "id": spare_part.id,
        "asset_id": spare_part.asset_id,
        "inventory_item_id": spare_part.inventory_item_id,
        "quantity": spare_part.quantity,
        "notes": spare_part.notes,
        "created_at": spare_part.created_at,
        "item_name": item.item_name,
        "part_number": item.part_number
    }


@app.put("/assets/{asset_id}/spare-parts/{spare_part_id}")
def update_asset_spare_part(
    asset_id: int,
    spare_part_id: int,
    update_data: AssetSparePartUpdate,
    session: Session = Depends(get_session)
):
    """Update quantity or notes for an asset's spare part"""
    spare_part = session.get(AssetSparePart, spare_part_id)
    if not spare_part or spare_part.asset_id != asset_id:
        raise HTTPException(status_code=404, detail="Spare part association not found")
    
    if update_data.quantity is not None:
        spare_part.quantity = update_data.quantity
    if update_data.notes is not None:
        spare_part.notes = update_data.notes
    
    session.add(spare_part)
    session.commit()
    session.refresh(spare_part)
    
    return spare_part


@app.delete("/assets/{asset_id}/spare-parts/{spare_part_id}")
def remove_spare_part_from_asset(
    asset_id: int,
    spare_part_id: int,
    session: Session = Depends(get_session)
):
    """Remove a spare part from an asset"""
    spare_part = session.get(AssetSparePart, spare_part_id)
    if not spare_part or spare_part.asset_id != asset_id:
        raise HTTPException(status_code=404, detail="Spare part association not found")
    
    session.delete(spare_part)
    session.commit()
    
    return {"message": "Spare part removed from asset successfully"}


@app.post("/assets/bulk-import")
async def bulk_import_assets(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """
    Bulk import assets from CSV file.
    Expected columns: asset_id, name, category, location_id, status, owner_cost_center, 
                     vendor, serial_number, tag_id, purchase_date, warranty_expiry
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    contents = await file.read()
    csv_data = io.StringIO(contents.decode('utf-8'))
    csv_reader = csv.DictReader(csv_data)
    
    imported_count = 0
    errors = []
    
    for row_num, row in enumerate(csv_reader, start=2):
        try:
            # Parse dates if present using helper function
            purchase_date = parse_date_string(row.get('purchase_date'))
            warranty_expiry = parse_date_string(row.get('warranty_expiry'))
            invoice_date = parse_date_string(row.get('invoice_date'))
            capitalised_on = parse_date_string(row.get('capitalised_on'))
            warranty_date = parse_date_string(row.get('warranty_date'))
            
            asset = Asset(
                asset_id=row['asset_id'],
                name=row['name'],
                category=row['category'],
                status=row.get('status', AssetStatus.ACTIVE),
                location_id=int(row['location_id']) if row.get('location_id') else None,
                station_id=int(row['station_id']) if row.get('station_id') else None,
                owner_cost_center=row.get('owner_cost_center'),
                vendor_name=row.get('vendor'),  # Use vendor_name instead of vendor
                vendor_id=int(row['vendor_id']) if row.get('vendor_id') else None,
                serial_number=row.get('serial_number'),
                tag_id=row.get('tag_id'),
                sap_id=row.get('sap_id'),
                purchase_date=purchase_date,
                warranty_expiry=warranty_expiry,
                warranty_date=warranty_date,
                invoice_date=invoice_date,
                capitalised_on=capitalised_on,
                invoice_number=row.get('invoice_number'),
                purchase_cost=float(row['purchase_cost']) if row.get('purchase_cost') else None,
                company_code=row.get('company_code', 'IN07'),
                plant_code=row.get('plant_code', 'IN08'),
                currency=row.get('currency', 'INR'),
                location_name=row.get('location_name', 'Plant - Bangalore'),
                state=row.get('state'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(asset)
            imported_count += 1
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    session.commit()
    
    return {
        "imported": imported_count,
        "errors": errors
    }


# ============================================
# WORK ORDER ENDPOINTS
# ============================================
@app.post("/work-orders", response_model=WorkOrder)
def create_work_order(
    work_order: WorkOrder, 
    asset_ids: List[int] = Query([]),
    session: Session = Depends(get_session)
):
    # Convert date strings to Python datetime objects
    work_order = convert_work_order_dates(work_order)
    
    # Ensure datetime fields are datetime objects
    work_order.created_at = datetime.utcnow()
    session.add(work_order)
    session.commit()
    session.refresh(work_order)
    
    # Link assets
    for asset_id in asset_ids:
        link = WorkOrderAsset(work_order_id=work_order.id, asset_id=asset_id)
        session.add(link)
    
    session.commit()
    return work_order


@app.get("/work-orders", response_model=List[WorkOrder])
def get_work_orders(
    status: Optional[WorkOrderStatus] = None,
    priority: Optional[WorkOrderPriority] = None,
    technician: Optional[str] = None,
    session: Session = Depends(get_session)
):
    query = select(WorkOrder)
    
    if status:
        query = query.where(WorkOrder.status == status)
    if priority:
        query = query.where(WorkOrder.priority == priority)
    if technician:
        query = query.where(WorkOrder.technician == technician)
    
    work_orders = session.exec(query).all()
    return work_orders


@app.get("/work-orders/{wo_id}", response_model=WorkOrder)
def get_work_order(wo_id: int, session: Session = Depends(get_session)):
    wo = session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    return wo


@app.patch("/work-orders/{wo_id}/assign")
def assign_work_order(wo_id: int, technician: str, session: Session = Depends(get_session)):
    wo = session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    wo.technician = technician
    if wo.status == WorkOrderStatus.OPEN:
        wo.status = WorkOrderStatus.IN_PROGRESS
        wo.started_at = datetime.utcnow()
    
    session.add(wo)
    session.commit()
    session.refresh(wo)
    return wo


@app.patch("/work-orders/{wo_id}/status")
def update_work_order_status(
    wo_id: int, 
    status: WorkOrderStatus,
    completion_notes: Optional[str] = None,
    time_spent: Optional[float] = None,
    session: Session = Depends(get_session)
):
    wo = session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    wo.status = status
    
    if status == WorkOrderStatus.IN_PROGRESS and not wo.started_at:
        wo.started_at = datetime.utcnow()
    
    if status == WorkOrderStatus.COMPLETED:
        wo.completed_at = datetime.utcnow()
        if completion_notes:
            wo.completion_notes = completion_notes
        if time_spent:
            wo.time_spent_hours = time_spent
    
    session.add(wo)
    session.commit()
    session.refresh(wo)
    return wo


@app.post("/work-orders/{wo_id}/assets/{asset_id}")
def link_asset_to_work_order(wo_id: int, asset_id: int, session: Session = Depends(get_session)):
    # Verify both exist
    wo = session.get(WorkOrder, wo_id)
    asset = session.get(Asset, asset_id)
    
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    link = WorkOrderAsset(work_order_id=wo_id, asset_id=asset_id)
    session.add(link)
    session.commit()
    return {"message": "Asset linked to Work Order"}


@app.get("/work-orders/{wo_id}/assets")
def get_work_order_assets(wo_id: int, session: Session = Depends(get_session)):
    links = session.exec(select(WorkOrderAsset).where(WorkOrderAsset.work_order_id == wo_id)).all()
    asset_ids = [link.asset_id for link in links]
    assets = session.exec(select(Asset).where(Asset.id.in_(asset_ids))).all()
    return assets


# ============================================
# PREVENTIVE MAINTENANCE ENDPOINTS
# ============================================
@app.post("/pm-templates", response_model=PMTemplate)
def create_pm_template(pm: PMTemplate, session: Session = Depends(get_session)):
    # Convert date strings to Python datetime objects
    pm = convert_pm_template_dates(pm)
    
    # Ensure datetime fields are datetime objects
    pm.created_at = datetime.utcnow()
    
    # Calculate next due date
    if pm.frequency_unit == PMFrequencyUnit.DAYS:
        pm.next_due_date = datetime.utcnow() + timedelta(days=pm.frequency_value)
    elif pm.frequency_unit == PMFrequencyUnit.MONTHS:
        pm.next_due_date = datetime.utcnow() + timedelta(days=pm.frequency_value * 30)
    
    session.add(pm)
    session.commit()
    session.refresh(pm)
    return pm


@app.get("/pm-templates", response_model=List[PMTemplate])
def get_pm_templates(
    asset_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    query = select(PMTemplate)
    
    if asset_id:
        query = query.where(PMTemplate.asset_id == asset_id)
    if is_active is not None:
        query = query.where(PMTemplate.is_active == is_active)
    
    templates = session.exec(query).all()
    return templates


@app.get("/pm-templates/due-soon")
def get_due_soon_pms(days: int = 7, session: Session = Depends(get_session)):
    """Get PM templates that are due within the specified number of days"""
    threshold_date = datetime.utcnow() + timedelta(days=days)
    
    query = select(PMTemplate).where(
        PMTemplate.is_active == True,
        PMTemplate.next_due_date <= threshold_date
    )
    
    due_pms = session.exec(query).all()
    return due_pms


@app.post("/pm-templates/{pm_id}/generate-wo")
def generate_work_order_from_pm(pm_id: int, session: Session = Depends(get_session)):
    pm = session.get(PMTemplate, pm_id)
    if not pm:
        raise HTTPException(status_code=404, detail="PM Template not found")
    
    # Generate WO number
    wo_count = len(session.exec(select(WorkOrder)).all())
    wo_number = f"WO-PM-{wo_count + 1:05d}"
    
    # Create Work Order
    work_order = WorkOrder(
        wo_number=wo_number,
        summary=pm.wo_summary_template,
        description=pm.wo_description_template,
        priority=pm.default_priority,
        status=WorkOrderStatus.OPEN,
        pm_template_id=pm.id
    )
    
    session.add(work_order)
    session.commit()
    session.refresh(work_order)
    
    # Link to asset
    link = WorkOrderAsset(work_order_id=work_order.id, asset_id=pm.asset_id)
    session.add(link)
    
    # Update PM template
    pm.last_generated_date = datetime.utcnow()
    
    # Calculate next due date
    if pm.frequency_unit == PMFrequencyUnit.DAYS:
        pm.next_due_date = datetime.utcnow() + timedelta(days=pm.frequency_value)
    elif pm.frequency_unit == PMFrequencyUnit.MONTHS:
        pm.next_due_date = datetime.utcnow() + timedelta(days=pm.frequency_value * 30)
    
    session.add(pm)
    session.commit()
    
    return work_order


# ============================================
# SPARE PARTS ENDPOINTS
# ============================================
@app.post("/inventory", response_model=InventoryItem)
def create_inventory_item(item: InventoryItem, session: Session = Depends(get_session)):
    # Convert date strings to Python datetime objects
    item = convert_inventory_item_dates(item)
    
    # Ensure datetime fields are datetime objects
    item.created_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    session.add(item)
    
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        # Handle specific constraint violations
        if "UNIQUE constraint failed: inventory_items.part_number" in str(e):
            raise HTTPException(status_code=400, detail=f"Part number '{item.part_number}' already exists. Please use a unique part number.")
        else:
            # Re-raise other errors with more context
            raise HTTPException(status_code=400, detail=f"Error creating spare part: {str(e)}")
    
    session.refresh(item)
    return item


@app.get("/inventory", response_model=List[InventoryItem])
def get_inventory_items(
    low_stock: bool = False,
    session: Session = Depends(get_session)
):
    query = select(InventoryItem)
    
    if low_stock:
        query = query.where(InventoryItem.stock_on_hand <= InventoryItem.min_stock)
    
    items = session.exec(query).all()
    
    # Compute verification status for each spare part
    for item in items:
        if item.id:
            item.physically_verified = compute_spare_part_verification_status(item.id, session)
    
    return items


@app.get("/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Spare part not found")
    
    # Compute verification status
    if item.id:
        item.physically_verified = compute_spare_part_verification_status(item.id, session)
    
    return item


@app.put("/inventory/{item_id}", response_model=InventoryItem)
def update_inventory_item(
    item_id: int, 
    item_update: InventoryItem, 
    session: Session = Depends(get_session)
):
    db_item = session.get(InventoryItem, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Spare part not found")
    
    # Convert date strings to Python datetime objects
    item_update = convert_inventory_item_dates(item_update)
    
    item_data = item_update.dict(exclude_unset=True)
    item_data["updated_at"] = datetime.utcnow()
    
    # Update item fields
    for key, value in item_data.items():
        if key not in ['created_at'] and hasattr(db_item, key):
            setattr(db_item, key, value)
    
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


@app.post("/work-orders/{wo_id}/parts")
def add_parts_to_work_order(
    wo_id: int,
    inventory_item_id: int,
    quantity: int,
    session: Session = Depends(get_session)
):
    """Add spare parts to work order and deduct from inventory"""
    wo = session.get(WorkOrder, wo_id)
    item = session.get(InventoryItem, inventory_item_id)
    
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    if not item:
        raise HTTPException(status_code=404, detail="Spare part not found")
    
    if item.stock_on_hand < quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    # Create usage record
    usage = WorkOrderPart(
        work_order_id=wo_id,
        inventory_item_id=inventory_item_id,
        quantity_used=quantity
    )
    session.add(usage)
    
    # Deduct from inventory (only when WO is completed)
    if wo.status == WorkOrderStatus.COMPLETED:
        item.stock_on_hand -= quantity
        item.updated_at = datetime.utcnow()
        session.add(item)
    
    session.commit()
    return {"message": "Spare parts added to work order", "remaining_stock": item.stock_on_hand}


@app.get("/work-orders/{wo_id}/parts")
def get_work_order_parts(wo_id: int, session: Session = Depends(get_session)):
    """Get all spare parts used in a work order"""
    parts = session.exec(
        select(WorkOrderPart).where(WorkOrderPart.work_order_id == wo_id)
    ).all()
    
    result = []
    for part in parts:
        item = session.get(InventoryItem, part.inventory_item_id)
        result.append({
            "part_number": item.part_number,
            "item_name": item.item_name,
            "quantity_used": part.quantity_used,
            "unit_cost": item.unit_cost,
            "total_cost": item.unit_cost * part.quantity_used if item.unit_cost else None
        })
    
    return result


# ============================================
# PHYSICAL VERIFICATION ENDPOINTS
# ============================================
@app.get("/physical-verification", response_model=List[PhysicalVerification])
def get_physical_verifications(session: Session = Depends(get_session)):
    """Get all physical verification records"""
    try:
        verifications = session.exec(select(PhysicalVerification)).all()
        return verifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching physical verifications: {str(e)}")


@app.get("/physical-verification/{verification_id}", response_model=PhysicalVerification)
def get_physical_verification(verification_id: int, session: Session = Depends(get_session)):
    """Get a specific physical verification record"""
    try:
        verification = session.get(PhysicalVerification, verification_id)
        if not verification:
            raise HTTPException(status_code=404, detail="Physical verification record not found")
        return verification
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching physical verification: {str(e)}")


@app.post("/physical-verification", response_model=PhysicalVerification)
def create_physical_verification(verification: PhysicalVerification, session: Session = Depends(get_session)):
    """Create a new physical verification record"""
    try:
        # Convert date strings to Python date/datetime objects
        verification = convert_physical_verification_dates(verification)
        
        verification.created_at = datetime.utcnow()
        verification.updated_at = datetime.utcnow()
        session.add(verification)
        session.commit()
        session.refresh(verification)
        return verification
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating physical verification: {str(e)}")


@app.put("/physical-verification/{verification_id}", response_model=PhysicalVerification)
def update_physical_verification(
    verification_id: int,
    verification_data: dict,
    session: Session = Depends(get_session)
):
    """Update a physical verification record"""
    try:
        verification = session.get(PhysicalVerification, verification_id)
        if not verification:
            raise HTTPException(status_code=404, detail="Physical verification record not found")
        
        # Convert date strings to proper Python date/datetime objects
        if 'phy_ver_date' in verification_data and isinstance(verification_data['phy_ver_date'], str):
            verification_data['phy_ver_date'] = parse_datetime_string(verification_data['phy_ver_date'])
        if 'next_pv_planned_date' in verification_data and isinstance(verification_data['next_pv_planned_date'], str):
            verification_data['next_pv_planned_date'] = parse_date_string(verification_data['next_pv_planned_date'])
        
        for key, value in verification_data.items():
            if hasattr(verification, key):
                setattr(verification, key, value)
        
        verification.updated_at = datetime.utcnow()
        session.add(verification)
        session.commit()
        session.refresh(verification)
        return verification
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating physical verification: {str(e)}")


@app.delete("/physical-verification/{verification_id}")
def delete_physical_verification(verification_id: int, session: Session = Depends(get_session)):
    """Delete a physical verification record"""
    try:
        verification = session.get(PhysicalVerification, verification_id)
        if not verification:
            raise HTTPException(status_code=404, detail="Physical verification record not found")
        
        session.delete(verification)
        session.commit()
        return {"message": "Physical verification record deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting physical verification: {str(e)}")


@app.get("/physical-verification/asset/{asset_id}", response_model=List[PhysicalVerification])
def get_physical_verifications_by_asset(asset_id: int, session: Session = Depends(get_session)):
    """Get all physical verification records for a specific asset"""
    try:
        verifications = session.exec(
            select(PhysicalVerification).where(PhysicalVerification.asset_id == asset_id)
        ).all()
        return verifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching physical verifications for asset: {str(e)}")


@app.get("/physical-verification/spare-part/{spare_part_id}", response_model=List[PhysicalVerification])
def get_physical_verifications_by_spare_part(spare_part_id: int, session: Session = Depends(get_session)):
    """Get all physical verification records for a specific spare part"""
    try:
        verifications = session.exec(
            select(PhysicalVerification).where(PhysicalVerification.spare_part_id == spare_part_id)
        ).all()
        return verifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching physical verifications for spare part: {str(e)}")


# ============================================
# UTILITY ENDPOINTS
# ============================================
@app.get("/stats/dashboard")
def get_dashboard_stats(session: Session = Depends(get_session)):
    """Get overall statistics for dashboard"""
    total_assets = len(session.exec(select(Asset)).all())
    active_assets = len(session.exec(select(Asset).where(Asset.status == AssetStatus.ACTIVE)).all())
    
    total_wos = len(session.exec(select(WorkOrder)).all())
    open_wos = len(session.exec(select(WorkOrder).where(WorkOrder.status == WorkOrderStatus.OPEN)).all())
    in_progress_wos = len(session.exec(select(WorkOrder).where(WorkOrder.status == WorkOrderStatus.IN_PROGRESS)).all())
    
    low_stock_items = len(session.exec(
        select(InventoryItem).where(InventoryItem.stock_on_hand <= InventoryItem.min_stock)
    ).all())
    
    due_pms = len(session.exec(
        select(PMTemplate).where(
            PMTemplate.is_active == True,
            PMTemplate.next_due_date <= datetime.utcnow() + timedelta(days=7)
        )
    ).all())
    
    return {
        "total_assets": total_assets,
        "active_assets": active_assets,
        "total_work_orders": total_wos,
        "open_work_orders": open_wos,
        "in_progress_work_orders": in_progress_wos,
        "low_stock_items": low_stock_items,
        "due_pms_next_7_days": due_pms
    }



