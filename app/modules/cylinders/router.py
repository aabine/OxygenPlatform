from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.modules.auth.deps import get_current_active_user
from app.modules.users.schemas import User
from app.modules.users.enums import UserRole
from app.modules.cylinders import schemas
from app.modules.cylinders.service import CylinderService
from app.modules.cylinders.enums import CylinderStatus

router = APIRouter(prefix="/cylinders", tags=["cylinders"])

@router.post("/", response_model=schemas.Cylinder)
async def create_cylinder(
    cylinder_in: schemas.CylinderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new cylinder (vendor only)"""
    if current_user.role != UserRole.VENDOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only vendors can create cylinders"
        )
    
    cylinder_service = CylinderService(db)
    return await cylinder_service.create(cylinder_in, current_user.id)

@router.get("/", response_model=List[schemas.Cylinder])
async def list_cylinders(
    status: CylinderStatus | None = None,
    is_assigned: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List cylinders.
    - Vendors see only their cylinders
    - Admins see all cylinders
    - Hospitals see cylinders in their current orders
    """
    cylinder_service = CylinderService(db)
    
    # Vendors see only their cylinders
    vendor_id = None
    if current_user.role == UserRole.VENDOR:
        vendor_id = current_user.id
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return await cylinder_service.list(
        vendor_id=vendor_id,
        status=status,
        is_assigned=is_assigned,
        skip=skip,
        limit=limit
    )

@router.get("/{cylinder_id}", response_model=schemas.CylinderWithLogs)
async def get_cylinder(
    cylinder_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get cylinder details with history logs.
    - Vendors can only see their cylinders
    - Admins can see all cylinders
    - Hospitals can see cylinders in their orders
    """
    cylinder_service = CylinderService(db)
    cylinder = await cylinder_service.get(cylinder_id)
    
    if not cylinder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cylinder not found"
        )
    
    # Check permissions
    if (current_user.role == UserRole.VENDOR and
        cylinder.vendor_id != current_user.id and
        current_user.role != UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Get cylinder logs
    logs = await cylinder_service.get_logs(cylinder_id)
    return {**cylinder.__dict__, "logs": logs}

@router.put("/{cylinder_id}", response_model=schemas.Cylinder)
async def update_cylinder(
    cylinder_id: int,
    cylinder_in: schemas.CylinderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update cylinder.
    - Vendors can only update their cylinders
    - Admins can update any cylinder
    """
    cylinder_service = CylinderService(db)
    cylinder = await cylinder_service.get(cylinder_id)
    
    if not cylinder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cylinder not found"
        )
    
    # Check permissions
    if (current_user.role == UserRole.VENDOR and
        cylinder.vendor_id != current_user.id and
        current_user.role != UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return await cylinder_service.update(cylinder_id, cylinder_in, current_user.id)

@router.post("/bulk-status-update", response_model=List[schemas.Cylinder])
async def update_cylinder_status_bulk(
    status_update: schemas.CylinderStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update status for multiple cylinders.
    - Vendors can only update their cylinders
    - Admins can update any cylinder
    """
    cylinder_service = CylinderService(db)
    
    # Verify permissions for all cylinders
    for cylinder_id in status_update.cylinder_ids:
        cylinder = await cylinder_service.get(cylinder_id)
        if not cylinder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cylinder {cylinder_id} not found"
            )
        
        if (current_user.role == UserRole.VENDOR and
            cylinder.vendor_id != current_user.id and
            current_user.role != UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions for cylinder {cylinder_id}"
            )
    
    return await cylinder_service.update_status_bulk(
        cylinder_ids=status_update.cylinder_ids,
        new_status=status_update.new_status,
        location=status_update.location,
        notes=status_update.notes,
        user_id=current_user.id
    )

@router.delete("/{cylinder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cylinder(
    cylinder_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete cylinder.
    - Vendors can only delete their cylinders
    - Admins can delete any cylinder
    """
    cylinder_service = CylinderService(db)
    cylinder = await cylinder_service.get(cylinder_id)
    
    if not cylinder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cylinder not found"
        )
    
    # Check permissions
    if (current_user.role == UserRole.VENDOR and
        cylinder.vendor_id != current_user.id and
        current_user.role != UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    if not await cylinder_service.delete(cylinder_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cylinder not found"
        )
