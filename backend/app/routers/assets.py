from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Asset
from ..schemas import AssetCreate, AssetOut, AssetUpdate

router = APIRouter(prefix="/api/assets", tags=["Actifs"],
                   dependencies=[Depends(get_current_user)])
writer = Depends(require_role("admin", "analyste"))


def _get(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(404, "Actif introuvable")
    return asset


def _name_free(db: Session, name: str, exclude_id: int | None = None) -> None:
    other = db.scalar(select(Asset).where(Asset.name == name))
    if other and other.id != exclude_id:
        raise HTTPException(409, "Un actif porte déjà ce nom")


@router.get("", response_model=list[AssetOut])
def list_assets(db: Session = Depends(get_db)):
    return [AssetOut.model_validate(a) for a in db.scalars(select(Asset).order_by(Asset.name))]


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    return AssetOut.model_validate(_get(db, asset_id))


@router.post("", response_model=AssetOut, status_code=201, dependencies=[writer])
def create_asset(data: AssetCreate, db: Session = Depends(get_db)):
    _name_free(db, data.name)
    asset = Asset(**data.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return AssetOut.model_validate(asset)


@router.put("/{asset_id}", response_model=AssetOut, dependencies=[writer])
def update_asset(asset_id: int, data: AssetUpdate, db: Session = Depends(get_db)):
    asset = _get(db, asset_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is None and key != "description":
            continue
        if key == "name":
            _name_free(db, value, asset.id)
        setattr(asset, key, value)
    db.commit()
    db.refresh(asset)
    return AssetOut.model_validate(asset)


@router.delete("/{asset_id}", status_code=204, dependencies=[writer])
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    db.delete(_get(db, asset_id))
    db.commit()
