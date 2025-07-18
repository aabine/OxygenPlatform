from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.cache import cache
from app.modules.cylinders.models import Cylinder, CylinderLog
from app.modules.cylinders.schemas import (
    CylinderCreate,
    CylinderUpdate,
    CylinderLogCreate,
    Location
)
from app.modules.cylinders.enums import CylinderStatus, CylinderEventType
from fastapi import HTTPException, status

class CylinderService:
    CACHE_PREFIX = "cylinder"
    
    def __init__(self, db: Session):
        self.db = db

    async def _cache_cylinder(self, cylinder: Cylinder) -> None:
        """Cache cylinder data"""
        if cylinder:
            await cache.set(
                [self.CACHE_PREFIX, cylinder.id],
                {
                    "id": cylinder.id,
                    "serial_number": cylinder.serial_number,
                    "status": cylinder.status,
                    "vendor_id": cylinder.vendor_id,
                    "location": cylinder.location,
                    "is_assigned": cylinder.is_assigned,
                    "current_order_id": cylinder.current_order_id
                }
            )

    async def _invalidate_cylinder_cache(self, cylinder_id: int) -> None:
        """Invalidate cylinder cache"""
        await cache.delete([self.CACHE_PREFIX, cylinder_id])
        await cache.invalidate_pattern(f"{self.CACHE_PREFIX}:list:*")

    async def create(
        self,
        cylinder_in: CylinderCreate,
        vendor_id: int
    ) -> Cylinder:
        """Create a new cylinder"""
        # Check if serial number is unique
        existing = await self.get_by_serial_number(cylinder_in.serial_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Serial number already registered"
            )

        # Create cylinder
        db_cylinder = Cylinder(
            **cylinder_in.model_dump(),
            vendor_id=vendor_id
        )
        self.db.add(db_cylinder)
        self.db.commit()
        self.db.refresh(db_cylinder)

        # Log creation
        await self.create_log(
            CylinderLogCreate(
                cylinder_id=db_cylinder.id,
                event_type=CylinderEventType.CREATED,
                new_status=db_cylinder.status,
                location=cylinder_in.location,
                created_by=vendor_id,
                notes="Cylinder created"
            )
        )

        await self._cache_cylinder(db_cylinder)
        return db_cylinder

    async def get(self, cylinder_id: int) -> Optional[Cylinder]:
        """Get cylinder by ID"""
        # Try cache first
        cached = await cache.get([self.CACHE_PREFIX, cylinder_id])
        if cached:
            stmt = select(Cylinder).where(Cylinder.id == cylinder_id)
            return self.db.execute(stmt).scalar_one_or_none()

        # Query database
        stmt = select(Cylinder).where(Cylinder.id == cylinder_id)
        cylinder = self.db.execute(stmt).scalar_one_or_none()
        if cylinder:
            await self._cache_cylinder(cylinder)
        return cylinder

    async def get_by_serial_number(self, serial_number: str) -> Optional[Cylinder]:
        """Get cylinder by serial number"""
        stmt = select(Cylinder).where(Cylinder.serial_number == serial_number)
        return self.db.execute(stmt).scalar_one_or_none()

    async def list(
        self,
        vendor_id: Optional[int] = None,
        status: Optional[CylinderStatus] = None,
        is_assigned: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Cylinder]:
        """List cylinders with filters"""
        stmt = select(Cylinder)
        
        if vendor_id:
            stmt = stmt.where(Cylinder.vendor_id == vendor_id)
        if status:
            stmt = stmt.where(Cylinder.status == status)
        if is_assigned is not None:
            stmt = stmt.where(Cylinder.is_assigned == is_assigned)
        
        stmt = stmt.offset(skip).limit(limit)
        return self.db.execute(stmt).scalars().all()

    async def update(
        self,
        cylinder_id: int,
        cylinder_in: CylinderUpdate,
        user_id: int
    ) -> Cylinder:
        """Update cylinder"""
        cylinder = await self.get(cylinder_id)
        if not cylinder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cylinder not found"
            )

        update_data = cylinder_in.model_dump(exclude_unset=True)
        old_status = cylinder.status
        
        # Update cylinder fields
        for field, value in update_data.items():
            setattr(cylinder, field, value)

        # Create log entry if status changed
        if cylinder_in.status and cylinder_in.status != old_status:
            await self.create_log(
                CylinderLogCreate(
                    cylinder_id=cylinder.id,
                    event_type=CylinderEventType.STATUS_CHANGED,
                    old_status=old_status,
                    new_status=cylinder_in.status,
                    location=cylinder_in.location,
                    created_by=user_id,
                    order_id=cylinder.current_order_id
                )
            )

        self.db.commit()
        self.db.refresh(cylinder)
        await self._cache_cylinder(cylinder)
        return cylinder

    async def update_status_bulk(
        self,
        cylinder_ids: List[int],
        new_status: CylinderStatus,
        location: Optional[Location] = None,
        notes: Optional[str] = None,
        user_id: int = None,
        order_id: Optional[int] = None
    ) -> List[Cylinder]:
        """Update status for multiple cylinders"""
        updated_cylinders = []
        
        for cyl_id in cylinder_ids:
            cylinder = await self.get(cyl_id)
            if cylinder:
                old_status = cylinder.status
                cylinder.status = new_status
                if location:
                    cylinder.location = location.model_dump()
                
                # Create log entry
                await self.create_log(
                    CylinderLogCreate(
                        cylinder_id=cylinder.id,
                        event_type=CylinderEventType.STATUS_CHANGED,
                        old_status=old_status,
                        new_status=new_status,
                        location=location,
                        notes=notes,
                        created_by=user_id,
                        order_id=order_id
                    )
                )
                
                updated_cylinders.append(cylinder)
                await self._cache_cylinder(cylinder)

        self.db.commit()
        return updated_cylinders

    async def create_log(self, log_in: CylinderLogCreate) -> CylinderLog:
        """Create a new cylinder log entry"""
        db_log = CylinderLog(**log_in.model_dump())
        self.db.add(db_log)
        self.db.commit()
        self.db.refresh(db_log)
        return db_log

    async def get_logs(
        self,
        cylinder_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[CylinderLog]:
        """Get cylinder history logs"""
        stmt = (
            select(CylinderLog)
            .where(CylinderLog.cylinder_id == cylinder_id)
            .order_by(CylinderLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

    async def delete(self, cylinder_id: int, user_id: int) -> bool:
        """Delete a cylinder (soft delete by marking as inactive)"""
        cylinder = await self.get(cylinder_id)
        if cylinder:
            # Create deletion log
            await self.create_log(
                CylinderLogCreate(
                    cylinder_id=cylinder.id,
                    event_type=CylinderEventType.DELETED,
                    old_status=cylinder.status,
                    created_by=user_id,
                    notes="Cylinder deleted"
                )
            )
            
            await self._invalidate_cylinder_cache(cylinder_id)
            self.db.delete(cylinder)
            self.db.commit()
            return True
        return False
