# Asset Manager API Documentation

A comprehensive Asset Management System with FastAPI, SQLModel, and SQLite - inspired by IBM Maximo.

## Features

1. **Asset Registry** - Complete CRUD operations for assets
2. **Work Orders** - Create, assign, track, and complete work orders
3. **Preventive Maintenance** - Schedule and auto-generate PM work orders
4. **Inventory Management** - Track spare parts and usage

## Getting Started

### Installation

```bash
pip install -r requirements.txt
```

### Run the Server

```bash
uvicorn main:app --reload
```

The API will be available at: `http://localhost:8000`

Interactive API docs: `http://localhost:8000/docs`

## API Endpoints

### 🏢 Locations

#### Create Location
```http
POST /locations
Content-Type: application/json

{
  "name": "Building A - Floor 1",
  "description": "Main production floor",
  "parent_id": null
}
```

#### Get All Locations
```http
GET /locations
```

---

### 🏭 Asset Registry

#### Create Asset
```http
POST /assets
Content-Type: application/json

{
  "asset_id": "ASSET-001",
  "name": "Hydraulic Press",
  "category": "Production Equipment",
  "status": "Active",
  "location_id": 1,
  "owner_cost_center": "PROD-001",
  "vendor": "Acme Industrial",
  "serial_number": "SN-12345",
  "tag_id": "TAG-001",
  "purchase_date": "2023-01-15",
  "warranty_expiry": "2025-01-15",
  "purchase_cost": 50000.00
}
```

#### Get All Assets (with filters)
```http
GET /assets?status=Active&category=Production Equipment
GET /assets?search=Hydraulic
GET /assets?location_id=1
```

#### Get Single Asset
```http
GET /assets/{asset_id}
```

#### Update Asset
```http
PUT /assets/{asset_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "status": "In Maintenance"
}
```

#### Retire Asset
```http
PATCH /assets/{asset_id}/retire
```

#### Bulk Import Assets from CSV
```http
POST /assets/bulk-import
Content-Type: multipart/form-data

file: assets.csv
```

**CSV Format:**
```csv
asset_id,name,category,location_id,status,owner_cost_center,vendor,serial_number,tag_id,purchase_date,warranty_expiry
ASSET-001,Machine A,Production,1,Active,DEPT-001,Vendor A,SN001,TAG001,2023-01-01,2025-01-01
ASSET-002,Machine B,Production,1,Active,DEPT-001,Vendor B,SN002,TAG002,2023-02-01,2025-02-01
```

---

### 🔧 Work Orders

#### Create Work Order
```http
POST /work-orders?asset_ids=1&asset_ids=2
Content-Type: application/json

{
  "wo_number": "WO-2024-001",
  "summary": "Replace hydraulic pump",
  "description": "The pump is making unusual noises",
  "priority": "High",
  "status": "Open",
  "due_date": "2024-12-15T10:00:00"
}
```

#### Get All Work Orders (with filters)
```http
GET /work-orders
GET /work-orders?status=Open
GET /work-orders?priority=High
GET /work-orders?technician=John Doe
```

#### Get Single Work Order
```http
GET /work-orders/{wo_id}
```

#### Assign Work Order to Technician
```http
PATCH /work-orders/{wo_id}/assign?technician=John Doe
```

#### Update Work Order Status
```http
PATCH /work-orders/{wo_id}/status?status=Completed&time_spent=2.5
Content-Type: application/json

{
  "completion_notes": "Pump replaced successfully"
}
```

#### Link Asset to Work Order
```http
POST /work-orders/{wo_id}/assets/{asset_id}
```

#### Get Work Order Assets
```http
GET /work-orders/{wo_id}/assets
```

---

### 🔄 Preventive Maintenance

#### Create PM Template
```http
POST /pm-templates
Content-Type: application/json

{
  "name": "Quarterly Inspection",
  "description": "Regular quarterly maintenance check",
  "frequency_value": 90,
  "frequency_unit": "Days",
  "asset_id": 1,
  "wo_summary_template": "Quarterly Inspection - {asset_name}",
  "wo_description_template": "Perform regular quarterly inspection",
  "default_priority": "Medium",
  "is_active": true
}
```

#### Get All PM Templates
```http
GET /pm-templates
GET /pm-templates?asset_id=1
GET /pm-templates?is_active=true
```

#### Get Due Soon PMs
```http
GET /pm-templates/due-soon?days=7
```

#### Generate Work Order from PM Template
```http
POST /pm-templates/{pm_id}/generate-wo
```

---

### 📦 Inventory Management

#### Create Inventory Item
```http
POST /inventory
Content-Type: application/json

{
  "item_name": "Hydraulic Oil Filter",
  "part_number": "HF-001",
  "description": "Standard hydraulic filter",
  "stock_on_hand": 50,
  "min_stock": 10,
  "max_stock": 100,
  "unit_cost": 25.50
}
```

#### Get All Inventory Items
```http
GET /inventory
GET /inventory?low_stock=true
```

#### Get Single Inventory Item
```http
GET /inventory/{item_id}
```

#### Update Inventory Item
```http
PUT /inventory/{item_id}
Content-Type: application/json

{
  "stock_on_hand": 45
}
```

#### Add Parts to Work Order
```http
POST /work-orders/{wo_id}/parts?inventory_item_id=1&quantity=2
```

**Note:** Parts are automatically deducted from inventory when the work order status is set to "Completed".

#### Get Work Order Parts
```http
GET /work-orders/{wo_id}/parts
```

---

### 📊 Dashboard & Statistics

#### Get Dashboard Stats
```http
GET /stats/dashboard
```

**Response:**
```json
{
  "total_assets": 150,
  "active_assets": 135,
  "total_work_orders": 500,
  "open_work_orders": 25,
  "in_progress_work_orders": 12,
  "low_stock_items": 5,
  "due_pms_next_7_days": 8
}
```

---

## Data Models

### Asset Status
- `Active`
- `Inactive`
- `In Maintenance`
- `Retired`

### Work Order Status
- `Open`
- `In Progress`
- `Completed`
- `Cancelled`

### Work Order Priority
- `Low`
- `Medium`
- `High`
- `Critical`

### PM Frequency Units
- `Days`
- `Hours`
- `Months`

---

## Database Schema

The application uses SQLite with SQLModel ORM. The database file is created automatically as `asset_manager.db`.

### Tables:
- `locations` - Hierarchical location structure
- `assets` - Asset registry with all details
- `work_orders` - Work order tracking
- `work_order_assets` - Many-to-many relationship between WOs and Assets
- `pm_templates` - Preventive maintenance schedules
- `inventory_items` - Spare parts catalog
- `work_order_parts` - Parts usage tracking

---

## Workflow Examples

### Complete Asset Management Flow

1. **Create a Location**
   ```bash
   POST /locations
   ```

2. **Add an Asset**
   ```bash
   POST /assets
   ```

3. **Create a PM Template for the Asset**
   ```bash
   POST /pm-templates
   ```

4. **System generates PM Work Order**
   ```bash
   POST /pm-templates/{pm_id}/generate-wo
   ```

5. **Assign to Technician**
   ```bash
   PATCH /work-orders/{wo_id}/assign
   ```

6. **Add Parts to Work Order**
   ```bash
   POST /work-orders/{wo_id}/parts
   ```

7. **Complete the Work Order**
   ```bash
   PATCH /work-orders/{wo_id}/status?status=Completed
   ```
   *(Parts are automatically deducted from inventory)*

---

## Testing with cURL

### Create an Asset
```bash
curl -X POST "http://localhost:8000/assets" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "TEST-001",
    "name": "Test Machine",
    "category": "Production",
    "status": "Active"
  }'
```

### Get All Assets
```bash
curl "http://localhost:8000/assets"
```

### Create a Work Order
```bash
curl -X POST "http://localhost:8000/work-orders?asset_ids=1" \
  -H "Content-Type: application/json" \
  -d '{
    "wo_number": "WO-001",
    "summary": "Test Work Order",
    "priority": "Medium",
    "status": "Open"
  }'
```

---

## Features Summary

### ✅ Asset Registry
- [x] Create, View, Update, Retire assets
- [x] Full field support (ID, Name, Category, Location, Status, Owner, Vendor, Serial/Tag, Dates)
- [x] Bulk CSV import
- [x] Search and filtering
- [x] Location hierarchy support

### ✅ Work Orders
- [x] Create with summary, description, priority, due date, status
- [x] Assign to technician
- [x] Link multiple assets
- [x] Track time spent
- [x] Completion notes
- [x] Status transitions (Open → In Progress → Completed)

### ✅ Preventive Maintenance
- [x] PM templates with frequency (days/months/hours)
- [x] Auto-calculate next due date
- [x] Manual and scheduled WO generation
- [x] "Due Soon" tracking
- [x] Link to assets

### ✅ Inventory
- [x] Spare parts catalog
- [x] Part number, stock levels, min/max
- [x] Low stock alerts
- [x] Auto-deduct parts when WO completed
- [x] Cost tracking

---

## Maximo Feature Mapping

| Maximo Module | Implementation | Status |
|---------------|----------------|--------|
| Assets | Asset table with full fields | ✅ Complete |
| Locations | Location hierarchy | ✅ Complete |
| Item Master | Inventory items | ✅ Complete |
| Work Orders | Full WO lifecycle | ✅ Complete |
| Assignments | Technician assignment | ✅ Complete |
| PM | PM templates + auto-generation | ✅ Complete |
| Job Plans | PM templates (simplified) | ✅ Complete |
| Inventory | Stock tracking | ✅ Complete |
| Issues/Returns | Parts usage on WO | ✅ Complete |

---

## Next Steps / Enhancements

- [ ] Authentication & Authorization
- [ ] File attachments for assets/WOs
- [ ] Advanced reporting
- [ ] Email notifications for due PMs
- [ ] Mobile app support
- [ ] Barcode/QR code scanning
- [ ] Asset hierarchy (parent-child)
- [ ] Failure tracking & analytics
- [ ] SLA management
- [ ] Purchase order integration

---

## License

MIT

---

## Support

For questions or issues, please refer to the interactive API documentation at `/docs` endpoint.
