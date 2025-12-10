from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, SQLModel, create_engine, Session, Relationship, select, or_
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
    assets: List["Asset"] = Relationship(back_populates="location")
    

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
    
    # Location & Ownership
    location_id: Optional[int] = Field(default=None, foreign_key="locations.id")
    owner_cost_center: Optional[str] = None
    
    # Vendor & Identification
    vendor: Optional[str] = None
    serial_number: Optional[str] = Field(default=None, unique=True)
    tag_id: Optional[str] = Field(default=None, unique=True)
    
    # Purchase & Warranty
    purchase_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    purchase_cost: Optional[float] = None
    
    # Tracking
    meter_reading: Optional[float] = None  # For runtime-based PM
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    location: Optional[Location] = Relationship(back_populates="assets")
    work_orders: List["WorkOrderAsset"] = Relationship(back_populates="asset")
    pm_templates: List["PMTemplate"] = Relationship(back_populates="asset")


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
# Models - Inventory
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
    
    # Costing
    unit_cost: Optional[float] = None
    
    # Tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    work_order_usage: List["WorkOrderPart"] = Relationship(back_populates="inventory_item")


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
# ASSET REGISTRY ENDPOINTS
# ============================================
@app.post("/assets", response_model=Asset)
def create_asset(asset: Asset, session: Session = Depends(get_session)):
    # Ensure datetime fields are datetime objects, not strings
    asset.created_at = datetime.utcnow()
    asset.updated_at = datetime.utcnow()
    session.add(asset)
    session.commit()
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
    return assets


@app.get("/assets/{asset_id}", response_model=Asset)
def get_asset(asset_id: int, session: Session = Depends(get_session)):
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@app.put("/assets/{asset_id}", response_model=Asset)
def update_asset(asset_id: int, asset_update: Asset, session: Session = Depends(get_session)):
    db_asset = session.get(Asset, asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    asset_data = asset_update.dict(exclude_unset=True)
    asset_data["updated_at"] = datetime.utcnow()
    
    # Skip datetime fields that come as strings - they're already in the DB
    for key, value in asset_data.items():
        if key not in ['created_at', 'updated_at'] or not isinstance(value, str):
            setattr(db_asset, key, value)
    
    # Ensure updated_at is a datetime object
    db_asset.updated_at = datetime.utcnow()
    
    session.add(db_asset)
    session.commit()
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
            # Parse dates if present
            purchase_date = None
            warranty_expiry = None
            
            if row.get('purchase_date'):
                purchase_date = datetime.strptime(row['purchase_date'], '%Y-%m-%d').date()
            if row.get('warranty_expiry'):
                warranty_expiry = datetime.strptime(row['warranty_expiry'], '%Y-%m-%d').date()
            
            asset = Asset(
                asset_id=row['asset_id'],
                name=row['name'],
                category=row['category'],
                status=row.get('status', AssetStatus.ACTIVE),
                location_id=int(row['location_id']) if row.get('location_id') else None,
                owner_cost_center=row.get('owner_cost_center'),
                vendor=row.get('vendor'),
                serial_number=row.get('serial_number'),
                tag_id=row.get('tag_id'),
                purchase_date=purchase_date,
                warranty_expiry=warranty_expiry,
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
# INVENTORY ENDPOINTS
# ============================================
@app.post("/inventory", response_model=InventoryItem)
def create_inventory_item(item: InventoryItem, session: Session = Depends(get_session)):
    session.add(item)
    session.commit()
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
    return items


@app.get("/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@app.put("/inventory/{item_id}", response_model=InventoryItem)
def update_inventory_item(
    item_id: int, 
    item_update: InventoryItem, 
    session: Session = Depends(get_session)
):
    db_item = session.get(InventoryItem, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    item_data = item_update.dict(exclude_unset=True)
    item_data["updated_at"] = datetime.utcnow()
    
    # Skip datetime fields that come as strings - they're already in the DB
    for key, value in item_data.items():
        if key not in ['created_at', 'updated_at'] or not isinstance(value, str):
            setattr(db_item, key, value)
    
    # Ensure updated_at is a datetime object
    db_item.updated_at = datetime.utcnow()
    
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
    """Add parts to work order and deduct from inventory"""
    wo = session.get(WorkOrder, wo_id)
    item = session.get(InventoryItem, inventory_item_id)
    
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
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
    return {"message": "Parts added to work order", "remaining_stock": item.stock_on_hand}


@app.get("/work-orders/{wo_id}/parts")
def get_work_order_parts(wo_id: int, session: Session = Depends(get_session)):
    """Get all parts used in a work order"""
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



