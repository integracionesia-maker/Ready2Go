"""Schemas de razones sociales (contrato §6)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EmpresaResponse(BaseModel):
    id: int
    razon_social: str
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    rfc: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class EmpresaCreate(BaseModel):
    razon_social: str = Field(..., min_length=1, max_length=255)
    direccion: Optional[str] = Field(None, max_length=255)
    ciudad: Optional[str] = Field(None, max_length=120)
    rfc: Optional[str] = Field(None, max_length=20)
    is_active: bool = True


class EmpresaUpdate(BaseModel):
    razon_social: Optional[str] = Field(None, min_length=1, max_length=255)
    direccion: Optional[str] = Field(None, max_length=255)
    ciudad: Optional[str] = Field(None, max_length=120)
    rfc: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
