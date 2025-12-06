"""
Module DOT Configuration API
Endpoints for managing system-level default DOTs for each module
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from database.connection import get_db
from models.module_dot_config import ModuleDOTConfig, AVAILABLE_MODULES
from models.dot import DOT
from core.security import get_current_user
from models.user import User

router = APIRouter(prefix="/api/module-dot-config", tags=["Module DOT Configuration"])


# Schemas
class ModuleDOTConfigCreate(BaseModel):
    module: str
    dot_id: int


class ModuleDOTConfigResponse(BaseModel):
    id: int
    module: str
    dot_id: int
    dot_name: str | None = None

    class Config:
        from_attributes = True


class ModuleListResponse(BaseModel):
    modules: List[str]


# Endpoints
@router.get("/modules", response_model=ModuleListResponse)
async def list_available_modules(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of all available modules.
    """
    return ModuleListResponse(modules=AVAILABLE_MODULES)


@router.get("", response_model=List[ModuleDOTConfigResponse])
async def get_all_module_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all module DOT configurations.
    Only accessible by superusers/staff.
    """
    if not (current_user.is_superuser or current_user.is_staff):
        raise HTTPException(status_code=403, detail="Only superusers and staff can view module configurations")

    configs = db.query(ModuleDOTConfig).all()

    result = []
    for config in configs:
        dot = db.query(DOT).filter(DOT.id == config.dot_id).first()
        result.append(ModuleDOTConfigResponse(
            id=config.id,
            module=config.module,
            dot_id=config.dot_id,
            dot_name=dot.name if dot else None
        ))

    return result


@router.get("/{module}", response_model=ModuleDOTConfigResponse)
async def get_module_config(
    module: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get DOT configuration for a specific module.
    """
    if module not in AVAILABLE_MODULES:
        raise HTTPException(status_code=400, detail=f"Invalid module. Must be one of: {', '.join(AVAILABLE_MODULES)}")

    config = db.query(ModuleDOTConfig).filter(ModuleDOTConfig.module == module).first()

    if not config:
        raise HTTPException(status_code=404, detail=f"No DOT configuration found for module '{module}'")

    dot = db.query(DOT).filter(DOT.id == config.dot_id).first()

    return ModuleDOTConfigResponse(
        id=config.id,
        module=config.module,
        dot_id=config.dot_id,
        dot_name=dot.name if dot else None
    )


@router.post("", response_model=ModuleDOTConfigResponse)
async def create_module_config(
    config_data: ModuleDOTConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update a module DOT configuration.
    Only accessible by superusers/staff.
    """
    if not (current_user.is_superuser or current_user.is_staff):
        raise HTTPException(status_code=403, detail="Only superusers and staff can manage module configurations")

    if config_data.module not in AVAILABLE_MODULES:
        raise HTTPException(status_code=400, detail=f"Invalid module. Must be one of: {', '.join(AVAILABLE_MODULES)}")

    # Verify DOT exists
    dot = db.query(DOT).filter(DOT.id == config_data.dot_id).first()
    if not dot:
        raise HTTPException(status_code=404, detail=f"DOT with id {config_data.dot_id} not found")

    # Check if configuration already exists
    existing_config = db.query(ModuleDOTConfig).filter(
        ModuleDOTConfig.module == config_data.module
    ).first()

    if existing_config:
        # Update existing configuration
        existing_config.dot_id = config_data.dot_id
        db.commit()
        db.refresh(existing_config)

        return ModuleDOTConfigResponse(
            id=existing_config.id,
            module=existing_config.module,
            dot_id=existing_config.dot_id,
            dot_name=dot.name
        )
    else:
        # Create new configuration
        new_config = ModuleDOTConfig(
            module=config_data.module,
            dot_id=config_data.dot_id
        )
        db.add(new_config)
        db.commit()
        db.refresh(new_config)

        return ModuleDOTConfigResponse(
            id=new_config.id,
            module=new_config.module,
            dot_id=new_config.dot_id,
            dot_name=dot.name
        )


@router.put("/{module}", response_model=ModuleDOTConfigResponse)
async def update_module_config(
    module: str,
    dot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update DOT configuration for a specific module.
    Only accessible by superusers/staff.
    """
    if not (current_user.is_superuser or current_user.is_staff):
        raise HTTPException(status_code=403, detail="Only superusers and staff can manage module configurations")

    if module not in AVAILABLE_MODULES:
        raise HTTPException(status_code=400, detail=f"Invalid module. Must be one of: {', '.join(AVAILABLE_MODULES)}")

    # Verify DOT exists
    dot = db.query(DOT).filter(DOT.id == dot_id).first()
    if not dot:
        raise HTTPException(status_code=404, detail=f"DOT with id {dot_id} not found")

    config = db.query(ModuleDOTConfig).filter(ModuleDOTConfig.module == module).first()

    if not config:
        raise HTTPException(status_code=404, detail=f"No DOT configuration found for module '{module}'")

    config.dot_id = dot_id
    db.commit()
    db.refresh(config)

    return ModuleDOTConfigResponse(
        id=config.id,
        module=config.module,
        dot_id=config.dot_id,
        dot_name=dot.name
    )


@router.delete("/{module}")
async def delete_module_config(
    module: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove DOT configuration for a specific module.
    Only accessible by superusers/staff.
    """
    if not (current_user.is_superuser or current_user.is_staff):
        raise HTTPException(status_code=403, detail="Only superusers and staff can manage module configurations")

    if module not in AVAILABLE_MODULES:
        raise HTTPException(status_code=400, detail=f"Invalid module. Must be one of: {', '.join(AVAILABLE_MODULES)}")

    config = db.query(ModuleDOTConfig).filter(ModuleDOTConfig.module == module).first()

    if not config:
        raise HTTPException(status_code=404, detail=f"No DOT configuration found for module '{module}'")

    db.delete(config)
    db.commit()

    return {"message": f"DOT configuration for module '{module}' has been removed"}
