from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.models.db import ProductAttribute, get_engine
from app.models.schemas import ProductAttributeIn, ProductAttributeOut, ProductAttributeUpdate

router = APIRouter()


def _to_out(row: ProductAttribute) -> ProductAttributeOut:
    return ProductAttributeOut(
        id=row.id or 0,
        key=row.key,
        label=row.label,
        aliases=row.aliases_list(),
        hint=row.hint,
        sort_order=row.sort_order,
        active=row.active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[ProductAttributeOut])
def list_attributes(include_inactive: bool = True) -> list[ProductAttributeOut]:
    with Session(get_engine()) as session:
        query = select(ProductAttribute).order_by(ProductAttribute.sort_order, ProductAttribute.label)
        if not include_inactive:
            query = query.where(ProductAttribute.active.is_(True))
        rows = session.exec(query).all()
    return [_to_out(row) for row in rows]


@router.post("", response_model=ProductAttributeOut, status_code=201)
def create_attribute(body: ProductAttributeIn) -> ProductAttributeOut:
    now = datetime.now(timezone.utc)
    row = ProductAttribute(
        key=body.key,
        label=body.label.strip(),
        hint=body.hint,
        sort_order=body.sort_order,
        active=body.active,
        created_at=now,
        updated_at=now,
    )
    row.set_aliases([a.strip() for a in body.aliases if a.strip()])
    with Session(get_engine()) as session:
        existing = session.exec(select(ProductAttribute).where(ProductAttribute.key == body.key)).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Attribute key already exists: {body.key}")
        session.add(row)
        session.commit()
        session.refresh(row)
    return _to_out(row)


@router.patch("/{attribute_id}", response_model=ProductAttributeOut)
def update_attribute(attribute_id: int, body: ProductAttributeUpdate) -> ProductAttributeOut:
    with Session(get_engine()) as session:
        row = session.get(ProductAttribute, attribute_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Attribute not found")
        if body.label is not None:
            row.label = body.label.strip()
        if body.aliases is not None:
            row.set_aliases([a.strip() for a in body.aliases if a.strip()])
        if body.hint is not None:
            row.hint = body.hint or None
        if body.sort_order is not None:
            row.sort_order = body.sort_order
        if body.active is not None:
            row.active = body.active
        row.updated_at = datetime.now(timezone.utc)
        session.add(row)
        session.commit()
        session.refresh(row)
    return _to_out(row)


@router.delete("/{attribute_id}", status_code=204)
def delete_attribute(attribute_id: int) -> None:
    with Session(get_engine()) as session:
        row = session.get(ProductAttribute, attribute_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Attribute not found")
        session.delete(row)
        session.commit()
