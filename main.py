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
import pandas as pd
from auth import create_db_and_seed, authenticate_user, create_token_for_user, get_user_by_token
from pydantic import BaseModel

# Import export service
from export_service import (
    export_work_orders_csv,
    export_assets_csv,
    export_inventory_csv,
    export_locations_csv,
    export_vendors_csv,
    export_work_orders_excel,
    export_assets_excel,
    export_inventory_excel,
    export_locations_excel,
    export_vendors_excel
)
import os

# ============================================
# Database Setup
# ============================================
# Use /tmp directory for SQLite on Vercel (serverless environment)
# For local development, use current directory
IS_VERCEL = os.getenv("VERCEL", False)
DB_DIR = "/tmp" if IS_VERCEL else "."
DATABASE_URL = f"sqlite:///{DB_DIR}/asset_manager.db"

# Different engine config for Vercel vs local
if IS_VERCEL:
    engine = create_engine(DATABASE_URL, echo=False)  # Disable echo on production
else:
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


class MaintenanceType(str, Enum):
    PREVENTIVE = "Preventive"
    CORRECTIVE = "Corrective"
    PREDICTIVE = "Predictive"
    BREAKDOWN = "Breakdown"


class DoneBy(str, Enum):
    INTERNAL = "Internal"
    EXTERNAL = "External"


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
    # Additional Fields for Enhanced PM Template
    maintenance_type: MaintenanceType = Field(default=MaintenanceType.PREVENTIVE)
    done_by: DoneBy = Field(default=DoneBy.INTERNAL)
    vendor_name: Optional[str] = None  # For external maintenance
    estimated_duration: Optional[float] = None  # in hours
    schedule_on: Optional[date] = None  # Scheduled date for PM
    
    # Tracking
    last_generated_date: Optional[datetime] = None  # Acts as completed_on
    next_due_date: Optional[datetime] = None  # Next scheduled date
    is_active: bool = Field(default=True)
    
    # Work Order Template
    wo_summary_template: str
    wo_description_template: Optional[str] = None
    default_priority: WorkOrderPriority = Field(default=WorkOrderPriority.MEDIUM)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    asset: Asset = Relationship(back_populates="pm_templates")
    generated_work_orders: List[WorkOrder] = Relationship(back_populates="pm_template")
    spare_parts: List["PMSparePart"] = Relationship(back_populates="pm_template")


# ============================================
# Models - PM Spare Parts Link Table
# ============================================
class PMSparePart(SQLModel, table=True):
    __tablename__ = "pm_spare_parts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    pm_template_id: int = Field(foreign_key="pm_templates.id")
    inventory_item_id: int = Field(foreign_key="inventory_items.id")
    quantity: int = Field(default=1)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    pm_template: PMTemplate = Relationship(back_populates="spare_parts")
    inventory_item: "InventoryItem" = Relationship(back_populates="pm_usage")


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
    pm_usage: List["PMSparePart"] = Relationship(back_populates="inventory_item")

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
# Request/Response Models for PM Templates
# ============================================
class SparePartLink(SQLModel):
    inventory_item_id: int
    quantity: int = 1
    notes: Optional[str] = None


class PMTemplateCreate(SQLModel):
    name: str
    description: Optional[str] = None
    frequency_value: int
    frequency_unit: PMFrequencyUnit = PMFrequencyUnit.DAYS
    asset_id: int
    maintenance_type: MaintenanceType = MaintenanceType.PREVENTIVE
    done_by: DoneBy = DoneBy.INTERNAL
    vendor_name: Optional[str] = None
    estimated_duration: Optional[float] = None
    schedule_on: Optional[date] = None
    wo_summary_template: str
    wo_description_template: Optional[str] = None
    default_priority: WorkOrderPriority = WorkOrderPriority.MEDIUM
    is_active: bool = True
    selectedSpareParts: List[SparePartLink] = []


class PMTemplateUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    frequency_value: Optional[int] = None
    frequency_unit: Optional[PMFrequencyUnit] = None
    maintenance_type: Optional[MaintenanceType] = None
    done_by: Optional[DoneBy] = None
    vendor_name: Optional[str] = None
    estimated_duration: Optional[float] = None
    schedule_on: Optional[date] = None
    wo_summary_template: Optional[str] = None
    wo_description_template: Optional[str] = None
    default_priority: Optional[WorkOrderPriority] = None
    is_active: Optional[bool] = None
    selectedSpareParts: Optional[List[SparePartLink]] = None


class PMTemplateResponse(SQLModel):
    id: int
    name: str
    description: Optional[str] = None
    frequency_value: int
    frequency_unit: PMFrequencyUnit
    asset_id: int
    maintenance_type: MaintenanceType
    done_by: DoneBy
    vendor_name: Optional[str] = None
    estimated_duration: Optional[float] = None
    schedule_on: Optional[date] = None
    last_generated_date: Optional[datetime] = None  # completed_on
    next_due_date: Optional[datetime] = None  # next_due
    is_active: bool
    wo_summary_template: str
    wo_description_template: Optional[str] = None
    default_priority: WorkOrderPriority
    created_at: datetime
    spare_parts: List[dict] = []
    asset: Optional[dict] = None


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

# CORS Middleware - Allow both localhost and production frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local Vite dev server
        "http://localhost:3000",  # Alternative local port
        "https://asset-blr-ui.vercel.app",  # Production frontend (current)
        "https://asset-blr-ltf4b4sj4-surajs-projects-a978d895.vercel.app",  # Old production frontend
        "https://*.vercel.app",  # All Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    create_db_and_seed()  # Creates default admin user
    
    # Note: On Vercel, /tmp database is ephemeral and will be recreated on cold starts
    # You can seed data via POST /init-demo-data endpoint after deployment
    if IS_VERCEL:
        print("🚀 Running on Vercel - Database using /tmp (ephemeral storage)")
        print("💡 Call POST /init-demo-data to seed sample data")


@app.get("/")
def read_root():
    return {"message": "Asset Manager API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    """Health check endpoint for Vercel"""
    return {
        "status": "healthy",
        "database": "connected",
        "environment": "vercel" if IS_VERCEL else "local"
    }


# ============================================
# LOCATION ENDPOINTS
# ============================================
@app.post("/locations", response_model=Location)
def create_location(location: Location, session: Session = Depends(get_session)):
     # Validate parent_id exists if provided
    if location.parent_id:
        parent = session.get(Location, location.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent location not found")
    
    session.add(location)
    session.commit()
    session.refresh(location)
    return location


@app.get("/locations", response_model=List[Location])
def get_locations(
    parent_id: Optional[int] = Query(None, description="Filter by parent location ID. Use 0 for root locations."),
    session: Session = Depends(get_session)
):
    """Get all locations, optionally filtered by parent_id"""
    if parent_id == 0:
        # Get root locations (no parent)
        locations = session.exec(select(Location).where(Location.parent_id == None)).all()
    elif parent_id is not None:
        # Get sub-locations of a specific parent
        locations = session.exec(select(Location).where(Location.parent_id == parent_id)).all()
    else:
        # Get all locations
        locations = session.exec(select(Location)).all()
    return locations
@app.get("/locations/{location_id}", response_model=Location)
def get_location(location_id: int, session: Session = Depends(get_session)):
    """Get a specific location by ID"""
    location = session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@app.get("/locations/{location_id}/sublocations", response_model=List[Location])
def get_sublocations(location_id: int, session: Session = Depends(get_session)):
    """Get all sub-locations for a specific parent location"""
    parent = session.get(Location, location_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent location not found")
    
    sublocations = session.exec(select(Location).where(Location.parent_id == location_id)).all()
    return sublocations


@app.put("/locations/{location_id}", response_model=Location)
def update_location(location_id: int, location_update: Location, session: Session = Depends(get_session)):
    """Update a location"""
    location = session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Validate parent_id if being updated
    if location_update.parent_id:
        if location_update.parent_id == location_id:
            raise HTTPException(status_code=400, detail="Location cannot be its own parent")
        parent = session.get(Location, location_update.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent location not found")
    
    location_data = location_update.dict(exclude_unset=True, exclude={'id'})
    for key, value in location_data.items():
        setattr(location, key, value)
    
    session.add(location)
    session.commit()
    session.refresh(location)
    return location


@app.delete("/locations/{location_id}")
def delete_location(location_id: int, session: Session = Depends(get_session)):
    """Delete a location"""
    location = session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Check if location has sub-locations
    sublocations = session.exec(select(Location).where(Location.parent_id == location_id)).all()
    if sublocations:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete location with {len(sublocations)} sub-location(s). Delete sub-locations first."
        )
    
    # Check if location has assets
    assets = session.exec(select(Asset).where(Asset.location_id == location_id)).all()
    if assets:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete location with {len(assets)} asset(s). Reassign assets first."
        )
    
    session.delete(location)
    session.commit()
    return {"message": "Location deleted successfully"}

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
def get_vendors(
    name: Optional[str] = None,
    contact_person: Optional[str] = None,
    email: Optional[str] = None,
    session: Session = Depends(get_session)
):
    query = select(Vendor)
    
    if name:
        query = query.where(Vendor.name.contains(name))
    if contact_person:
        query = query.where(Vendor.contact_person.contains(contact_person))
    if email:
        query = query.where(Vendor.email.contains(email))
    
    vendors = session.exec(query).all()
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
    asset_id: Optional[str] = None,
    name: Optional[str] = None,
    status: Optional[AssetStatus] = None,
    category: Optional[str] = None,
    location_id: Optional[int] = None,
    parent_asset_id: Optional[int] = None,
    serial_number: Optional[str] = None,
    search: Optional[str] = None,
    session: Session = Depends(get_session)
):
    query = select(Asset)
    
    # Specific field filters (exact or partial match)
    if asset_id:
        query = query.where(Asset.asset_id.contains(asset_id))
    if name:
        query = query.where(Asset.name.contains(name))
    if serial_number:
        query = query.where(Asset.serial_number.contains(serial_number))
    if status:
        query = query.where(Asset.status == status)
    if category:
        query = query.where(Asset.category == category)
    if location_id:
        query = query.where(Asset.location_id == location_id)
    if parent_asset_id:
        query = query.where(Asset.parent_asset_id == parent_asset_id)
    
    # General search (fallback for quick search)
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


@app.get("/assets/not-verified", response_model=List[Asset])
def get_assets_not_verified(session: Session = Depends(get_session)):
    """Get assets that have not been physically verified"""
    query = select(Asset).where(Asset.physically_verified == False)
    assets = session.exec(query).all()
    
    # Compute verification status for each asset (in case it's a computed field)
    for asset in assets:
        if asset.id:
            asset.physically_verified = compute_asset_verification_status(asset.id, session)
    
    # Filter only those that are still not verified
    return [asset for asset in assets if not asset.physically_verified]


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
    Bulk import assets from CSV, XLS, or XLSX file.
            Expected columns: asset_id, name, category, location_id, status, owner_cost_center, 
                     vendor, serial_number, tag_id, purchase_date, warranty_expiry
    """
    # Check file extension
    file_ext = file.filename.lower().split('.')[-1]
    if file_ext not in ['csv', 'xls', 'xlsx']:
        raise HTTPException(status_code=400, detail="File must be CSV, XLS, or XLSX")

    
    contents = await file.read()
    # Parse file based on extension
    try:
        if file_ext == 'csv':
            csv_data = io.StringIO(contents.decode('utf-8'))
            df = pd.read_csv(csv_data)
        else:  # xls or xlsx
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl' if file_ext == 'xlsx' else None)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
    
    # Replace NaN with None for proper handling
    df = df.where(pd.notnull(df), None)

    imported_count = 0
    errors = []
    
    for row_num, (_, row) in enumerate(df.iterrows(), start=2):
        try:
            # Helper function to safely get values and handle NaN
            def safe_get(key, default=None):
                val = row.get(key, default)
                # Check for NaN (pandas returns float NaN for empty cells)
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    return default
                # Convert empty strings to default
                if isinstance(val, str) and val.strip() == '':
                    return default
                return val
            
            def safe_int(key, default=None):
                val = safe_get(key)
                if val is None:
                    return default
                try:
                    return int(float(val))  # Convert through float first to handle strings like "1.0"
                except (ValueError, TypeError):
                    return default
            
            def safe_float(key, default=None):
                val = safe_get(key)
                if val is None:
                    return default
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default
            # Parse dates if present using helper function
            purchase_date = parse_date_string(safe_get('purchase_date'))
            warranty_expiry = parse_date_string(safe_get('warranty_expiry'))
            invoice_date = parse_date_string(safe_get('invoice_date'))
            capitalised_on = parse_date_string(safe_get('capitalised_on'))
            warranty_date = parse_date_string(safe_get('warranty_date'))
            
            asset = Asset(
                asset_id=str(safe_get('asset_id', '')),
                name=str(safe_get('name', '')),
                category=str(safe_get('category', '')),
                status=safe_get('status', AssetStatus.ACTIVE),
                location_id=safe_int('location_id'),
                station_id=safe_int('station_id'),
                owner_cost_center=safe_get('owner_cost_center'),
                vendor_name=safe_get('vendor'),  # Use vendor_name instead of vendor
                vendor_id=safe_int('vendor_id'),
                serial_number=safe_get('serial_number'),
                tag_id=safe_get('tag_id'),
                sap_id=safe_get('sap_id'),
                purchase_date=purchase_date,
                warranty_expiry=warranty_expiry,
                warranty_date=warranty_date,
                invoice_date=invoice_date,
                capitalised_on=capitalised_on,
                invoice_number=safe_get('invoice_number'),
                purchase_cost=safe_float('purchase_cost'),
                company_code=safe_get('company_code', 'IN07'),
                plant_code=safe_get('plant_code', 'IN08'),
                currency=safe_get('currency', 'INR'),
                location_name=safe_get('location_name', 'Plant - Bangalore'),
                state=safe_get('state'),
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
    summary: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[WorkOrderStatus] = None,
    priority: Optional[WorkOrderPriority] = None,
    technician: Optional[str] = None,
    asset_id: Optional[int] = None,
    due_date_preset: Optional[str] = None,  # next_week, next_month, overdue
    due_date_from: Optional[str] = None,  # Custom date range start (YYYY-MM-DD)
    due_date_to: Optional[str] = None,    # Custom date range end (YYYY-MM-DD)
    session: Session = Depends(get_session)
):
    from datetime import timedelta
    
    query = select(WorkOrder)
    
    if summary:
        query = query.where(WorkOrder.summary.contains(summary))
    if description:
        query = query.where(WorkOrder.description.contains(description))
    if status:
        query = query.where(WorkOrder.status == status)
    if priority:
        query = query.where(WorkOrder.priority == priority)
    if technician:
        query = query.where(WorkOrder.technician.contains(technician))
    if asset_id:
        # Filter work orders that have this asset
        subquery = select(WorkOrderAsset.work_order_id).where(WorkOrderAsset.asset_id == asset_id)
        query = query.where(WorkOrder.id.in_(subquery))
    
    # Date filtering
    if due_date_preset:
        now = datetime.utcnow()
        if due_date_preset == "next_week":
            start_date = now
            end_date = now + timedelta(days=7)
            query = query.where(WorkOrder.due_date >= start_date, WorkOrder.due_date <= end_date)
        elif due_date_preset == "next_month":
            start_date = now
            end_date = now + timedelta(days=30)
            query = query.where(WorkOrder.due_date >= start_date, WorkOrder.due_date <= end_date)
        elif due_date_preset == "overdue":
            query = query.where(WorkOrder.due_date < now, WorkOrder.status != WorkOrderStatus.COMPLETED)
    elif due_date_from or due_date_to:
        # Custom date range
        if due_date_from:
            from_date = datetime.strptime(due_date_from, "%Y-%m-%d")
            query = query.where(WorkOrder.due_date >= from_date)
        if due_date_to:
            to_date = datetime.strptime(due_date_to, "%Y-%m-%d")
            # Add 1 day to include the entire end date
            to_date = to_date + timedelta(days=1)
            query = query.where(WorkOrder.due_date < to_date)
    
    work_orders = session.exec(query).all()
    return work_orders


@app.get("/work-orders/due-next-week", response_model=List[WorkOrder])
def get_work_orders_due_next_week(session: Session = Depends(get_session)):
    """Get work orders due in the next 7 days"""
    today = date.today()
    next_week = today + timedelta(days=7)
    
    query = select(WorkOrder).where(
        WorkOrder.due_date != None,
        WorkOrder.due_date >= today,
        WorkOrder.due_date <= next_week,
        WorkOrder.status.in_([WorkOrderStatus.OPEN, WorkOrderStatus.IN_PROGRESS])
    )
    
    work_orders = session.exec(query).all()
    return work_orders


@app.get("/work-orders/overdue", response_model=List[WorkOrder])
def get_overdue_work_orders(session: Session = Depends(get_session)):
    """Get work orders that are past their due date"""
    today = date.today()
    
    query = select(WorkOrder).where(
        WorkOrder.due_date != None,
        WorkOrder.due_date < today,
        WorkOrder.status.in_([WorkOrderStatus.OPEN, WorkOrderStatus.IN_PROGRESS])
    )
    
    work_orders = session.exec(query).all()
    return work_orders


@app.get("/work-orders/{wo_id}", response_model=WorkOrder)
def get_work_order(wo_id: int, session: Session = Depends(get_session)):
    wo = session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    return wo

@app.put("/work-orders/{wo_id}", response_model=WorkOrder)
def update_work_order(wo_id: int, wo_update: WorkOrder, session: Session = Depends(get_session)):
    """Update a work order"""
    db_wo = session.get(WorkOrder, wo_id)
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    # Store old status to check for transitions
    old_status = db_wo.status
    
    # Get update data, excluding unset fields
    wo_data = wo_update.dict(exclude_unset=True)
    
    # Update work order fields
    for key, value in wo_data.items():
        if key not in ['id', 'wo_number', 'created_at'] and hasattr(db_wo, key):
            setattr(db_wo, key, value)
    
    # Handle status transitions
    if 'status' in wo_data:
        new_status = wo_data['status']
        
        # Setting timestamps
        if new_status == WorkOrderStatus.IN_PROGRESS and not db_wo.started_at:
            db_wo.started_at = datetime.utcnow()
        elif new_status == WorkOrderStatus.COMPLETED and not db_wo.completed_at:
            db_wo.completed_at = datetime.utcnow()
        
        # Handle inventory restoration when reverting from COMPLETED
        if old_status == WorkOrderStatus.COMPLETED and new_status in [WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.OPEN]:
            # Restore all spare parts to inventory
            parts = session.exec(
                select(WorkOrderPart).where(WorkOrderPart.work_order_id == wo_id)
            ).all()
            
            for part in parts:
                item = session.get(InventoryItem, part.inventory_item_id)
                if item:
                    item.stock_on_hand += part.quantity_used
                    item.updated_at = datetime.utcnow()
                    session.add(item)
        
        # Deduct inventory again when changing back to COMPLETED
        elif old_status in [WorkOrderStatus.OPEN, WorkOrderStatus.IN_PROGRESS] and new_status == WorkOrderStatus.COMPLETED:
            # Deduct all spare parts from inventory
            parts = session.exec(
                select(WorkOrderPart).where(WorkOrderPart.work_order_id == wo_id)
            ).all()
            
            for part in parts:
                item = session.get(InventoryItem, part.inventory_item_id)
                if item:
                    if item.stock_on_hand < part.quantity_used:
                        session.rollback()
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Insufficient stock for {item.item_name}. Required: {part.quantity_used}, Available: {item.stock_on_hand}"
                        )
                    item.stock_on_hand -= part.quantity_used
                    item.updated_at = datetime.utcnow()
                    session.add(item)
    
    session.add(db_wo)
    
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Error updating work order: {str(e)}")
    
    session.refresh(db_wo)
    return db_wo

@app.patch("/work-orders/{wo_id}/start")
def start_work_order(wo_id: int, session: Session = Depends(get_session)):
    """Start a work order - sets status to IN_PROGRESS and records start time"""
    wo = session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    wo.status = WorkOrderStatus.IN_PROGRESS
    if not wo.started_at:
        wo.started_at = datetime.utcnow()
    
    session.add(wo)
    session.commit()
    session.refresh(wo)
    return wo


@app.patch("/work-orders/{wo_id}/complete")
def complete_work_order(
    wo_id: int,
    completion_notes: Optional[str] = None,
    time_spent_hours: Optional[float] = None,
    session: Session = Depends(get_session)
):
    """Complete a work order - sets status to COMPLETED and records completion time"""
    wo = session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    wo.status = WorkOrderStatus.COMPLETED
    wo.completed_at = datetime.utcnow()
    
    if completion_notes:
        wo.completion_notes = completion_notes
    if time_spent_hours:
        wo.time_spent_hours = time_spent_hours
    
    session.add(wo)
    session.commit()
    session.refresh(wo)
    return wo


@app.patch("/work-orders/{wo_id}/cancel")
def cancel_work_order(wo_id: int, session: Session = Depends(get_session)):
    """Cancel a work order - sets status to CANCELLED"""
    wo = session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    wo.status = WorkOrderStatus.CANCELLED
    
    session.add(wo)
    session.commit()
    session.refresh(wo)
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
        # Auto-update PM template if this work order is linked to one
        if wo.pm_template_id:
            pm_template = session.get(PMTemplate, wo.pm_template_id)
            if pm_template:
                # Update last generated date
                pm_template.last_generated_date = datetime.utcnow()
                
                # Recalculate next due date
                if pm_template.frequency_unit == PMFrequencyUnit.DAYS:
                    pm_template.next_due_date = datetime.utcnow() + timedelta(days=pm_template.frequency_value)
                elif pm_template.frequency_unit == PMFrequencyUnit.MONTHS:
                    pm_template.next_due_date = datetime.utcnow() + timedelta(days=pm_template.frequency_value * 30)
                elif pm_template.frequency_unit == PMFrequencyUnit.HOURS:
                    pm_template.next_due_date = datetime.utcnow() + timedelta(hours=pm_template.frequency_value)
                
                session.add(pm_template)
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
# EXPORT ENDPOINTS
# ============================================

@app.get("/work-orders/export/csv")
def export_work_orders_to_csv(
    summary: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[WorkOrderStatus] = None,
    priority: Optional[WorkOrderPriority] = None,
    technician: Optional[str] = None,
    asset_id: Optional[int] = None,
    due_date_preset: Optional[str] = None,
    due_date_from: Optional[str] = None,
    due_date_to: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Export filtered work orders to CSV"""
    from datetime import timedelta
    
    query = select(WorkOrder)
    
    # Apply same filters as get_work_orders
    if summary:
        query = query.where(WorkOrder.summary.contains(summary))
    if description:
        query = query.where(WorkOrder.description.contains(description))
    if status:
        query = query.where(WorkOrder.status == status)
    if priority:
        query = query.where(WorkOrder.priority == priority)
    if technician:
        query = query.where(WorkOrder.technician.contains(technician))
    if asset_id:
        subquery = select(WorkOrderAsset.work_order_id).where(WorkOrderAsset.asset_id == asset_id)
        query = query.where(WorkOrder.id.in_(subquery))
    
    # Date filtering
    if due_date_preset:
        now = datetime.utcnow()
        if due_date_preset == "next_week":
            start_date = now
            end_date = now + timedelta(days=7)
            query = query.where(WorkOrder.due_date >= start_date, WorkOrder.due_date <= end_date)
        elif due_date_preset == "next_month":
            start_date = now
            end_date = now + timedelta(days=30)
            query = query.where(WorkOrder.due_date >= start_date, WorkOrder.due_date <= end_date)
        elif due_date_preset == "overdue":
            query = query.where(WorkOrder.due_date < now, WorkOrder.status != WorkOrderStatus.COMPLETED)
    elif due_date_from or due_date_to:
        if due_date_from:
            from_date = datetime.strptime(due_date_from, "%Y-%m-%d")
            query = query.where(WorkOrder.due_date >= from_date)
        if due_date_to:
            to_date = datetime.strptime(due_date_to, "%Y-%m-%d")
            to_date = to_date + timedelta(days=1)
            query = query.where(WorkOrder.due_date < to_date)
    
    work_orders = session.exec(query).all()
    return export_work_orders_csv(work_orders)


@app.get("/assets/export/csv")
def export_assets_to_csv(
    asset_id: Optional[str] = None,
    name: Optional[str] = None,
    status: Optional[AssetStatus] = None,
    category: Optional[str] = None,
    location_id: Optional[int] = None,
    parent_asset_id: Optional[int] = None,
    serial_number: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Export filtered assets to CSV"""
    query = select(Asset)
    
    # Apply same filters as get_assets
    if asset_id:
        query = query.where(Asset.asset_id.contains(asset_id))
    if name:
        query = query.where(Asset.name.contains(name))
    if status:
        query = query.where(Asset.status == status)
    if category:
        query = query.where(Asset.category == category)
    if location_id:
        query = query.where(Asset.location_id == location_id)
    if parent_asset_id:
        query = query.where(Asset.parent_asset_id == parent_asset_id)
    if serial_number:
        query = query.where(Asset.serial_number.contains(serial_number))
    
    assets = session.exec(query).all()
    return export_assets_csv(assets)


@app.get("/inventory/export/csv")
def export_inventory_to_csv(
    item_name: Optional[str] = None,
    part_number: Optional[str] = None,
    status: Optional[InventoryStatus] = None,
    location_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    low_stock: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    """Export filtered inventory items to CSV"""
    query = select(InventoryItem)
    
    # Apply same filters as get_inventory
    if item_name:
        query = query.where(InventoryItem.item_name.contains(item_name))
    if part_number:
        query = query.where(InventoryItem.part_number.contains(part_number))
    if status:
        query = query.where(InventoryItem.status == status)
    if location_id:
        query = query.where(InventoryItem.location_id == location_id)
    if vendor_id:
        query = query.where(InventoryItem.vendor_id == vendor_id)
    if low_stock:
        query = query.where(InventoryItem.quantity <= InventoryItem.min_stock_level)
    
    items = session.exec(query).all()
    return export_inventory_csv(items)


@app.get("/locations/export/csv")
def export_locations_to_csv(
    name: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Export filtered locations to CSV"""
    query = select(Location)
    
    if name:
        query = query.where(Location.name.contains(name))
    
    locations = session.exec(query).all()
    return export_locations_csv(locations)


@app.get("/vendors/export/csv")
def export_vendors_to_csv(
    name: Optional[str] = None,
    contact_person: Optional[str] = None,
    email: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Export filtered vendors to CSV"""
    query = select(Vendor)
    
    if name:
        query = query.where(Vendor.name.contains(name))
    if contact_person:
        query = query.where(Vendor.contact_person.contains(contact_person))
    if email:
        query = query.where(Vendor.email.contains(email))
    
    vendors = session.exec(query).all()
    return export_vendors_csv(vendors)


# ============================================
# EXCEL EXPORT ENDPOINTS
# ============================================

@app.get("/work-orders/export/excel")
def export_work_orders_to_excel(
    summary: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[WorkOrderStatus] = None,
    priority: Optional[WorkOrderPriority] = None,
    technician: Optional[str] = None,
    asset_id: Optional[int] = None,
    due_date_preset: Optional[str] = None,
    due_date_from: Optional[str] = None,
    due_date_to: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Export filtered work orders to Excel"""
    from datetime import timedelta
    
    query = select(WorkOrder)
    
    # Apply same filters as get_work_orders
    if summary:
        query = query.where(WorkOrder.summary.contains(summary))
    if description:
        query = query.where(WorkOrder.description.contains(description))
    if status:
        query = query.where(WorkOrder.status == status)
    if priority:
        query = query.where(WorkOrder.priority == priority)
    if technician:
        query = query.where(WorkOrder.technician.contains(technician))
    if asset_id:
        subquery = select(WorkOrderAsset.work_order_id).where(WorkOrderAsset.asset_id == asset_id)
        query = query.where(WorkOrder.id.in_(subquery))
    
    # Date filtering
    if due_date_preset:
        now = datetime.utcnow()
        if due_date_preset == "next_week":
            start_date = now
            end_date = now + timedelta(days=7)
            query = query.where(WorkOrder.due_date >= start_date, WorkOrder.due_date <= end_date)
        elif due_date_preset == "next_month":
            start_date = now
            end_date = now + timedelta(days=30)
            query = query.where(WorkOrder.due_date >= start_date, WorkOrder.due_date <= end_date)
        elif due_date_preset == "overdue":
            query = query.where(WorkOrder.due_date < now, WorkOrder.status != WorkOrderStatus.COMPLETED)
    elif due_date_from or due_date_to:
        if due_date_from:
            from_date = datetime.strptime(due_date_from, "%Y-%m-%d")
            query = query.where(WorkOrder.due_date >= from_date)
        if due_date_to:
            to_date = datetime.strptime(due_date_to, "%Y-%m-%d")
            to_date = to_date + timedelta(days=1)
            query = query.where(WorkOrder.due_date < to_date)
    
    work_orders = session.exec(query).all()
    return export_work_orders_excel(work_orders)


@app.get("/assets/export/excel")
def export_assets_to_excel(
    asset_id: Optional[str] = None,
    name: Optional[str] = None,
    status: Optional[AssetStatus] = None,
    category: Optional[str] = None,
    location_id: Optional[int] = None,
    parent_asset_id: Optional[int] = None,
    serial_number: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Export filtered assets to Excel"""
    query = select(Asset)
    
    # Apply same filters as get_assets
    if asset_id:
        query = query.where(Asset.asset_id.contains(asset_id))
    if name:
        query = query.where(Asset.name.contains(name))
    if status:
        query = query.where(Asset.status == status)
    if category:
        query = query.where(Asset.category == category)
    if location_id:
        query = query.where(Asset.location_id == location_id)
    if parent_asset_id:
        query = query.where(Asset.parent_asset_id == parent_asset_id)
    if serial_number:
        query = query.where(Asset.serial_number.contains(serial_number))
    
    assets = session.exec(query).all()
    return export_assets_excel(assets)


@app.get("/inventory/export/excel")
def export_inventory_to_excel(
    item_name: Optional[str] = None,
    part_number: Optional[str] = None,
    status: Optional[InventoryStatus] = None,
    location_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    low_stock: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    """Export filtered inventory items to Excel"""
    query = select(InventoryItem)
    
    # Apply same filters as get_inventory
    if item_name:
        query = query.where(InventoryItem.item_name.contains(item_name))
    if part_number:
        query = query.where(InventoryItem.part_number.contains(part_number))
    if status:
        query = query.where(InventoryItem.status == status)
    if location_id:
        query = query.where(InventoryItem.location_id == location_id)
    if vendor_id:
        query = query.where(InventoryItem.vendor_id == vendor_id)
    if low_stock:
        query = query.where(InventoryItem.quantity <= InventoryItem.min_stock_level)
    
    items = session.exec(query).all()
    return export_inventory_excel(items)


@app.get("/locations/export/excel")
def export_locations_to_excel(
    name: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Export filtered locations to Excel"""
    query = select(Location)
    
    if name:
        query = query.where(Location.name.contains(name))
    
    locations = session.exec(query).all()
    return export_locations_excel(locations)


@app.get("/vendors/export/excel")
def export_vendors_to_excel(
    name: Optional[str] = None,
    contact_person: Optional[str] = None,
    email: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Export filtered vendors to Excel"""
    query = select(Vendor)
    
    if name:
        query = query.where(Vendor.name.contains(name))
    if contact_person:
        query = query.where(Vendor.contact_person.contains(contact_person))
    if email:
        query = query.where(Vendor.email.contains(email))
    
    vendors = session.exec(query).all()
    return export_vendors_excel(vendors)


# ============================================
# PREVENTIVE MAINTENANCE ENDPOINTS
# ============================================
@app.post("/pm-templates", response_model=PMTemplateResponse)
def create_pm_template(pm_data: PMTemplateCreate, session: Session = Depends(get_session)):
    # Verify asset exists
    asset = session.get(Asset, pm_data.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Create PM Template
    pm_template = PMTemplate(
        name=pm_data.name,
        description=pm_data.description,
        frequency_value=pm_data.frequency_value,
        frequency_unit=pm_data.frequency_unit,
        asset_id=pm_data.asset_id,
        maintenance_type=pm_data.maintenance_type,
        done_by=pm_data.done_by,
        vendor_name=pm_data.vendor_name,
        estimated_duration=pm_data.estimated_duration,
        schedule_on=pm_data.schedule_on,
        wo_summary_template=pm_data.wo_summary_template,
        wo_description_template=pm_data.wo_description_template,
        default_priority=pm_data.default_priority,
        is_active=pm_data.is_active,
        created_at=datetime.utcnow()
    )


    # Calculate next due date
    if pm_template.frequency_unit == PMFrequencyUnit.DAYS:
        pm_template.next_due_date = datetime.utcnow() + timedelta(days=pm_template.frequency_value)
    elif pm_template.frequency_unit == PMFrequencyUnit.MONTHS:
        pm_template.next_due_date = datetime.utcnow() + timedelta(days=pm_template.frequency_value * 30)
    elif pm_template.frequency_unit == PMFrequencyUnit.HOURS:
        # For hours-based, we'll set a default calculation
        pm_template.next_due_date = datetime.utcnow() + timedelta(hours=pm_template.frequency_value)
    
    session.add(pm_template)
    session.commit()
    session.refresh(pm_template)
    
    # Add spare parts links
    spare_parts_data = []
    if pm_data.selectedSpareParts:
        for spare_part in pm_data.selectedSpareParts:
            # Verify inventory item exists
            inventory_item = session.get(InventoryItem, spare_part.inventory_item_id)
            if not inventory_item:
                continue
            
            pm_spare_part = PMSparePart(
                pm_template_id=pm_template.id,
                inventory_item_id=spare_part.inventory_item_id,
                quantity=spare_part.quantity,
                notes=spare_part.notes,
                created_at=datetime.utcnow()
            )
            session.add(pm_spare_part)
            spare_parts_data.append({
                "id": spare_part.inventory_item_id,
                "inventory_item_id": spare_part.inventory_item_id,
                "item_name": inventory_item.item_name,
                "part_number": inventory_item.part_number,
                "quantity": spare_part.quantity,
                "notes": spare_part.notes
            })
        
        session.commit()
    
    # Prepare response
    return PMTemplateResponse(
        id=pm_template.id,
        name=pm_template.name,
        description=pm_template.description,
        frequency_value=pm_template.frequency_value,
        frequency_unit=pm_template.frequency_unit,
        asset_id=pm_template.asset_id,
        maintenance_type=pm_template.maintenance_type,
        done_by=pm_template.done_by,
        vendor_name=pm_template.vendor_name,
        estimated_duration=pm_template.estimated_duration,
        schedule_on=pm_template.schedule_on,
        last_generated_date=pm_template.last_generated_date,
        next_due_date=pm_template.next_due_date,
        is_active=pm_template.is_active,
        wo_summary_template=pm_template.wo_summary_template,
        wo_description_template=pm_template.wo_description_template,
        default_priority=pm_template.default_priority,
        created_at=pm_template.created_at,
        spare_parts=spare_parts_data,
        asset={
            "id": asset.id,
            "asset_id": asset.asset_id,
            "name": asset.name,
            "category": asset.category
        }
    )


@app.get("/pm-templates", response_model=List[PMTemplateResponse])
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
    # Build response with related data
    result = []
    for template in templates:
        # Get asset
        asset = session.get(Asset, template.asset_id)
        
        # Get spare parts
        spare_parts_links = session.exec(
            select(PMSparePart).where(PMSparePart.pm_template_id == template.id)
        ).all()
        
        spare_parts_data = []
        for link in spare_parts_links:
            inventory_item = session.get(InventoryItem, link.inventory_item_id)
            if inventory_item:
                spare_parts_data.append({
                    "id": link.id,
                    "inventory_item_id": link.inventory_item_id,
                    "item_name": inventory_item.item_name,
                    "part_number": inventory_item.part_number,
                    "quantity": link.quantity,
                    "notes": link.notes
                })
        
        result.append(PMTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            frequency_value=template.frequency_value,
            frequency_unit=template.frequency_unit,
            asset_id=template.asset_id,
            maintenance_type=template.maintenance_type,
            done_by=template.done_by,
            vendor_name=template.vendor_name,
            estimated_duration=template.estimated_duration,
            schedule_on=template.schedule_on,
            last_generated_date=template.last_generated_date,
            next_due_date=template.next_due_date,
            is_active=template.is_active,
            wo_summary_template=template.wo_summary_template,
            wo_description_template=template.wo_description_template,
            default_priority=template.default_priority,
            created_at=template.created_at,
            spare_parts=spare_parts_data,
            asset={
                "id": asset.id,
                "asset_id": asset.asset_id,
                "name": asset.name,
                "category": asset.category
            } if asset else None
        ))
    
    return result


@app.get("/pm-templates/{pm_id}", response_model=PMTemplateResponse)
def get_pm_template(pm_id: int, session: Session = Depends(get_session)):
    template = session.get(PMTemplate, pm_id)
    if not template:
        raise HTTPException(status_code=404, detail="PM Template not found")
    
    # Get asset
    asset = session.get(Asset, template.asset_id)
    
    # Get spare parts
    spare_parts_links = session.exec(
        select(PMSparePart).where(PMSparePart.pm_template_id == template.id)
    ).all()
    
    spare_parts_data = []
    for link in spare_parts_links:
        inventory_item = session.get(InventoryItem, link.inventory_item_id)
        if inventory_item:
            spare_parts_data.append({
                "id": link.id,
                "inventory_item_id": link.inventory_item_id,
                "item_name": inventory_item.item_name,
                "part_number": inventory_item.part_number,
                "quantity": link.quantity,
                "notes": link.notes
            })
    
    return PMTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        frequency_value=template.frequency_value,
        frequency_unit=template.frequency_unit,
        asset_id=template.asset_id,
        maintenance_type=template.maintenance_type,
        done_by=template.done_by,
        vendor_name=template.vendor_name,
        estimated_duration=template.estimated_duration,
        schedule_on=template.schedule_on,
        last_generated_date=template.last_generated_date,
        next_due_date=template.next_due_date,
        is_active=template.is_active,
        wo_summary_template=template.wo_summary_template,
        wo_description_template=template.wo_description_template,
        default_priority=template.default_priority,
        created_at=template.created_at,
        spare_parts=spare_parts_data,
        asset={
            "id": asset.id,
            "asset_id": asset.asset_id,
            "name": asset.name,
            "category": asset.category
        } if asset else None
    )

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


@app.get("/pm-templates/hours-due")
def get_hours_based_pms_due(session: Session = Depends(get_session)):
    """Get hours-based PM templates that are currently due"""
    query = select(PMTemplate).where(
        PMTemplate.frequency_unit == PMFrequencyUnit.HOURS,
        PMTemplate.is_active == True,
        PMTemplate.next_due_date != None,
        PMTemplate.next_due_date <= datetime.utcnow()
    )
    
    due_pms = session.exec(query).all()
    return due_pms


@app.put("/pm-templates/{pm_id}", response_model=PMTemplateResponse)
def update_pm_template(pm_id: int, pm_data: PMTemplateUpdate, session: Session = Depends(get_session)):
    pm_template = session.get(PMTemplate, pm_id)
    if not pm_template:
        raise HTTPException(status_code=404, detail="PM Template not found")
    
    # Update fields if provided
    if pm_data.name is not None:
        pm_template.name = pm_data.name
    if pm_data.description is not None:
        pm_template.description = pm_data.description
    if pm_data.frequency_value is not None:
        pm_template.frequency_value = pm_data.frequency_value
    if pm_data.frequency_unit is not None:
        pm_template.frequency_unit = pm_data.frequency_unit
    if pm_data.maintenance_type is not None:
        pm_template.maintenance_type = pm_data.maintenance_type
    if pm_data.done_by is not None:
        pm_template.done_by = pm_data.done_by
    if pm_data.vendor_name is not None:
        pm_template.vendor_name = pm_data.vendor_name
    if pm_data.estimated_duration is not None:
        pm_template.estimated_duration = pm_data.estimated_duration
    if pm_data.schedule_on is not None:
        pm_template.schedule_on = pm_data.schedule_on
    if pm_data.wo_summary_template is not None:
        pm_template.wo_summary_template = pm_data.wo_summary_template
    if pm_data.wo_description_template is not None:
        pm_template.wo_description_template = pm_data.wo_description_template
    if pm_data.default_priority is not None:
        pm_template.default_priority = pm_data.default_priority
    if pm_data.is_active is not None:
        pm_template.is_active = pm_data.is_active
    
    # Recalculate next due date if frequency changed
    if pm_data.frequency_value is not None or pm_data.frequency_unit is not None:
        if pm_template.frequency_unit == PMFrequencyUnit.DAYS:
            pm_template.next_due_date = datetime.utcnow() + timedelta(days=pm_template.frequency_value)
        elif pm_template.frequency_unit == PMFrequencyUnit.MONTHS:
            pm_template.next_due_date = datetime.utcnow() + timedelta(days=pm_template.frequency_value * 30)
        elif pm_template.frequency_unit == PMFrequencyUnit.HOURS:
            pm_template.next_due_date = datetime.utcnow() + timedelta(hours=pm_template.frequency_value)
    
    # Update spare parts if provided
    if pm_data.selectedSpareParts is not None:
        # Remove existing spare parts
        existing_parts = session.exec(
            select(PMSparePart).where(PMSparePart.pm_template_id == pm_id)
        ).all()
        for part in existing_parts:
            session.delete(part)
        
        # Add new spare parts
        for spare_part in pm_data.selectedSpareParts:
            inventory_item = session.get(InventoryItem, spare_part.inventory_item_id)
            if inventory_item:
                pm_spare_part = PMSparePart(
                    pm_template_id=pm_template.id,
                    inventory_item_id=spare_part.inventory_item_id,
                    quantity=spare_part.quantity,
                    notes=spare_part.notes,
                    created_at=datetime.utcnow()
                )
                session.add(pm_spare_part)
    
    session.add(pm_template)
    session.commit()
    session.refresh(pm_template)
    
    # Get asset
    asset = session.get(Asset, pm_template.asset_id)
    
    # Get spare parts
    spare_parts_links = session.exec(
        select(PMSparePart).where(PMSparePart.pm_template_id == pm_template.id)
    ).all()
    
    spare_parts_data = []
    for link in spare_parts_links:
        inventory_item = session.get(InventoryItem, link.inventory_item_id)
        if inventory_item:
            spare_parts_data.append({
                "id": link.id,
                "inventory_item_id": link.inventory_item_id,
                "item_name": inventory_item.item_name,
                "part_number": inventory_item.part_number,
                "quantity": link.quantity,
                "notes": link.notes
            })
    
    return PMTemplateResponse(
        id=pm_template.id,
        name=pm_template.name,
        description=pm_template.description,
        frequency_value=pm_template.frequency_value,
        frequency_unit=pm_template.frequency_unit,
        asset_id=pm_template.asset_id,
        maintenance_type=pm_template.maintenance_type,
        done_by=pm_template.done_by,
        vendor_name=pm_template.vendor_name,
        estimated_duration=pm_template.estimated_duration,
        schedule_on=pm_template.schedule_on,
        last_generated_date=pm_template.last_generated_date,
        next_due_date=pm_template.next_due_date,
        is_active=pm_template.is_active,
        wo_summary_template=pm_template.wo_summary_template,
        wo_description_template=pm_template.wo_description_template,
        default_priority=pm_template.default_priority,
        created_at=pm_template.created_at,
        spare_parts=spare_parts_data,
        asset={
            "id": asset.id,
            "asset_id": asset.asset_id,
            "name": asset.name,
            "category": asset.category
        } if asset else None
    )


@app.delete("/pm-templates/{pm_id}")
def delete_pm_template(pm_id: int, session: Session = Depends(get_session)):
    pm_template = session.get(PMTemplate, pm_id)
    if not pm_template:
        raise HTTPException(status_code=404, detail="PM Template not found")
    
    # Delete associated spare parts
    spare_parts = session.exec(
        select(PMSparePart).where(PMSparePart.pm_template_id == pm_id)
    ).all()
    for part in spare_parts:
        session.delete(part)
    
    # Delete the template
    session.delete(pm_template)
    session.commit()
    
    return {"message": "PM Template deleted successfully"}


@app.post("/pm-templates/{pm_id}/generate-wo")
def generate_work_order_from_pm(pm_id: int, session: Session = Depends(get_session)):
    pm = session.get(PMTemplate, pm_id)
    if not pm:
        raise HTTPException(status_code=404, detail="PM Template not found")
    
    # Get the asset to replace placeholders
    asset = session.get(Asset, pm.asset_id)
    asset_name = asset.name if asset else "Unknown Asset"
    
    # Generate WO number
    wo_count = len(session.exec(select(WorkOrder)).all())
    wo_number = f"WO-PM-{wo_count + 1:05d}"
    
    # Replace placeholders in templates
    summary = pm.wo_summary_template.replace("{asset_name}", asset_name)
    description = pm.wo_description_template.replace("{asset_name}", asset_name) if pm.wo_description_template else None
    
    # Create Work Order
    work_order = WorkOrder(
        wo_number=wo_number,
        summary=summary,
        description=description,
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
    
    # Copy spare parts from PM template to work order
    if pm.spare_parts:
        for pm_spare in pm.spare_parts:
            wo_spare = WorkOrderPart(
                work_order_id=work_order.id,
                inventory_item_id=pm_spare.inventory_item_id,
                quantity_used=pm_spare.quantity
            )
            session.add(wo_spare)
    
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
    item_name: Optional[str] = None,
    part_number: Optional[str] = None,
    status: Optional[str] = None,
    location_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    low_stock: bool = False,
    session: Session = Depends(get_session)
):
    query = select(InventoryItem)
    
    # Specific field filters
    if item_name:
        query = query.where(InventoryItem.item_name.contains(item_name))
    if part_number:
        query = query.where(InventoryItem.part_number.contains(part_number))
    if status:
        query = query.where(InventoryItem.status == status)
    if location_id:
        query = query.where(InventoryItem.location_id == location_id)
    if vendor_id:
        query = query.where(InventoryItem.vendor_id == vendor_id)
    if low_stock:
        query = query.where(InventoryItem.stock_on_hand <= InventoryItem.min_stock)
    
    items = session.exec(query).all()
    
    # Compute verification status for each spare part
    for item in items:
        if item.id:
            item.physically_verified = compute_spare_part_verification_status(item.id, session)
    
    return items


@app.get("/inventory/not-verified", response_model=List[InventoryItem])
def get_inventory_not_verified(session: Session = Depends(get_session)):
    """Get inventory items (spare parts) that have not been physically verified"""
    query = select(InventoryItem).where(InventoryItem.physically_verified == False)
    items = session.exec(query).all()
    
    # Compute verification status for each spare part (in case it's a computed field)
    for item in items:
        if item.id:
            item.physically_verified = compute_spare_part_verification_status(item.id, session)
    
    # Filter only those that are still not verified
    return [item for item in items if not item.physically_verified]


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


@app.get("/inventory/{item_id}/where-used")
def get_inventory_where_used(item_id: int, session: Session = Depends(get_session)):
    """Get all assets that use this spare part (where-used information)"""
    # Check if inventory item exists
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Spare part not found")
    
    # Get all asset-spare part relationships for this inventory item
    asset_spare_parts = session.exec(
        select(AssetSparePart).where(AssetSparePart.inventory_item_id == item_id)
    ).all()
    
    # Enrich with asset details
    result = []
    for asp in asset_spare_parts:
        asset = session.get(Asset, asp.asset_id)
        if asset:
            result.append({
                "asset_id": asset.asset_id,
                "asset_name": asset.name,
                "description": asset.notes or asset.name,  # Use notes as description, fallback to name
                "quantity": asp.quantity,
                "asset_category": asset.category,
                "asset_status": asset.status,
                "notes": asp.notes
            })
    
    return result


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
    
    # Deduct from inventory immediately when part is added
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
            "id": part.id,
            "part_number": item.part_number,
            "item_name": item.item_name,
            "quantity_used": part.quantity_used,
            "unit_cost": item.unit_cost,
            "total_cost": item.unit_cost * part.quantity_used if item.unit_cost else None
        })
    
    return result

@app.delete("/work-orders/{wo_id}/parts/{part_id}")
def delete_work_order_part(wo_id: int, part_id: int, session: Session = Depends(get_session)):
    """Delete a spare part from a work order and restore inventory"""
    part = session.get(WorkOrderPart, part_id)
    
    if not part or part.work_order_id != wo_id:
        raise HTTPException(status_code=404, detail="Part not found in this work order")
    
    # Get the inventory item to restore stock
    item = session.get(InventoryItem, part.inventory_item_id)
    if item:
        # Always restore inventory when deleting a part since stock was deducted when added
        item.stock_on_hand += part.quantity_used
        item.updated_at = datetime.utcnow()
        session.add(item)
    
    session.delete(part)
    session.commit()
    return {"message": "Spare part removed from work order"}



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
    today = date.today()
    next_week = today + timedelta(days=7)
    
    # Existing stats
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
    
    # New stats
    work_orders_due_next_week = len(session.exec(
        select(WorkOrder).where(
            WorkOrder.due_date != None,
            WorkOrder.due_date >= today,
            WorkOrder.due_date <= next_week,
            WorkOrder.status.in_([WorkOrderStatus.OPEN, WorkOrderStatus.IN_PROGRESS])
        )
    ).all())
    
    overdue_work_orders = len(session.exec(
        select(WorkOrder).where(
            WorkOrder.due_date != None,
            WorkOrder.due_date < today,
            WorkOrder.status.in_([WorkOrderStatus.OPEN, WorkOrderStatus.IN_PROGRESS])
        )
    ).all())
    
    assets_not_verified = len(session.exec(
        select(Asset).where(Asset.physically_verified == False)
    ).all())
    
    spares_not_verified = len(session.exec(
        select(InventoryItem).where(InventoryItem.physically_verified == False)
    ).all())
    
    # PM hours due (count of hours-based PMs that are overdue)
    pm_hours_due = len(session.exec(
        select(PMTemplate).where(
            PMTemplate.frequency_unit == PMFrequencyUnit.HOURS,
            PMTemplate.is_active == True,
            PMTemplate.next_due_date != None,
            PMTemplate.next_due_date <= datetime.utcnow()
        )
    ).all())
    
    # PM hours report - Total estimated hours for all due PMs (all frequency types)
    due_pms_all = session.exec(
        select(PMTemplate).where(
            PMTemplate.is_active == True,
            PMTemplate.next_due_date != None,
            PMTemplate.next_due_date <= datetime.utcnow()
        )
    ).all()
    #test
    total_pm_hours_due = sum([pm.estimated_duration for pm in due_pms_all if pm.estimated_duration])
    pm_count_due = len(due_pms_all)
    
    # Assets by status
    assets_by_status = {}
    for status in AssetStatus:
        count = len(session.exec(select(Asset).where(Asset.status == status)).all())
        assets_by_status[status.value] = count
    
    # Assets by state
    assets_by_state = {}
    for state in AssetState:
        count = len(session.exec(select(Asset).where(Asset.state == state)).all())
        assets_by_state[state.value] = count
    # Count assets with no state
    assets_by_state["Not Set"] = len(session.exec(select(Asset).where(Asset.state == None)).all())
    
    # Work orders by priority
    work_orders_by_priority = {}
    for priority in WorkOrderPriority:
        count = len(session.exec(select(WorkOrder).where(WorkOrder.priority == priority)).all())
        work_orders_by_priority[priority.value] = count
    
    # Financial metrics
    total_asset_value = sum([asset.purchase_cost for asset in session.exec(select(Asset)).all() if asset.purchase_cost])
    total_inventory_value = sum([
        (item.stock_on_hand * item.unit_cost) 
        for item in session.exec(select(InventoryItem)).all() 
        if item.unit_cost
    ])
    
    # Top 5 assets by maintenance frequency (work order count)
    from sqlalchemy import func
    top_assets_query = (
        select(Asset.id, Asset.asset_id, Asset.name, func.count(WorkOrderAsset.work_order_id).label('work_order_count'))
        .join(WorkOrderAsset, Asset.id == WorkOrderAsset.asset_id)
        .group_by(Asset.id, Asset.asset_id, Asset.name)
        .order_by(func.count(WorkOrderAsset.work_order_id).desc())
        .limit(5)
    )
    top_assets_raw = session.exec(top_assets_query).all()
    top_assets_by_maintenance = [
        {
            "asset_id": row[1],
            "asset_name": row[2],
            "work_order_count": row[3]
        }
        for row in top_assets_raw
    ]
    
    # Monthly work order completion trend (last 6 months)
    monthly_completions = []
    current_date = datetime.now()
    
    for i in range(5, -1, -1):  # Last 6 months
        # Calculate month boundaries
        year = current_date.year
        month = current_date.month - i
        
        # Handle year rollover
        while month <= 0:
            month += 12
            year -= 1
        
        month_start = datetime(year, month, 1, 0, 0, 0)
        
        # Calculate next month for end boundary
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        
        if i == 0:
            month_end = current_date
        else:
            month_end = datetime(next_year, next_month, 1, 0, 0, 0)
        
        completed_count = len(session.exec(
            select(WorkOrder).where(
                WorkOrder.status == WorkOrderStatus.COMPLETED,
                WorkOrder.completed_at >= month_start,
                WorkOrder.completed_at < month_end
            )
        ).all())
        
        month_name = month_start.strftime("%b %Y")
        monthly_completions.append({
            "month": month_name,
            "completed": completed_count
        })
    
    return {
        "total_assets": total_assets,
        "active_assets": active_assets,
        "total_work_orders": total_wos,
        "open_work_orders": open_wos,
        "in_progress_work_orders": in_progress_wos,
        "low_stock_items": low_stock_items,
        "pm_due_soon": due_pms,
        "work_orders_due_next_week": work_orders_due_next_week,
        "overdue_work_orders": overdue_work_orders,
        "assets_not_verified": assets_not_verified,
        "spares_not_verified": spares_not_verified,
        "pm_hours_due": pm_hours_due,
        "total_pm_hours_due": total_pm_hours_due,
        "pm_count_due": pm_count_due,
        "assets_by_status": assets_by_status,
        "assets_by_state": assets_by_state,
        "work_orders_by_priority": work_orders_by_priority,
        "total_asset_value": total_asset_value,
        "total_inventory_value": total_inventory_value,
        "top_assets_by_maintenance": top_assets_by_maintenance,
        "monthly_work_order_completions": monthly_completions
    }


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class AuthResponse(BaseModel):
    token: str
    user: Optional[dict] = None


@app.post("/auth/login")
def auth_login(credentials: dict):
    username = credentials.get("username")
    password = credentials.get("password")
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token_for_user(user.id)
    return {"token": token, "user": {"id": user.id, "username": user.username, "email": user.email}}


@app.post("/auth/signup", response_model=AuthResponse)
def signup(request: SignupRequest):
    """Register a new user"""
    from auth import get_session as get_auth_session, _hash_password, User
    
    session = get_auth_session()
    
    try:
        # Check if username already exists
        stmt = select(User).where(User.username == request.username)
        existing_user = session.exec(stmt).first()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Create new user
        new_user = User(
            username=request.username,
            email=request.email,
            password_hash=_hash_password(request.password),
            is_active=True
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        
        # Generate token
        token = create_token_for_user(new_user.id)
        
        return AuthResponse(
            token=token,
            user={"id": new_user.id, "username": new_user.username, "email": new_user.email}
        )
    except Exception as e:
        session.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()

