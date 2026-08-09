from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Optional, Any



class UserCreate(BaseModel):
    email: str
    phone: Optional[str] = None
    password: str
    name: str
    avatar_url: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    phone: Optional[str] = None
    name: str
    rating: float
    registration_date: datetime
    avatar_url: Optional[str] = None

class CategoryCreate(BaseModel):
    name: str
    slug: str
    parent_category_id: Optional[int] = None
    level: int = 0


class CategoryResponse(CategoryCreate):
    id: int



class AttributeCreate(BaseModel):
    category_id: int
    name: str
    slug: str
    data_type: str
    is_filterable: bool = False
    unit: Optional[str] = None

class AttributeResponse(AttributeCreate):
    id: int


class AdvertisementCreate(BaseModel):
    user_id: int
    category_id: int
    title: str
    description: Optional[str] = None
    price: int
    status: str = "draft"
    city: int
    address: Optional[str] = None
    params: Dict[str, Any] = {}

class AdvertisementResponse(AdvertisementCreate):
    id: int
    views_count: int
    created_at: datetime
    updated_at: datetime

class ImageCreate(BaseModel):
    ad_id: int
    url: str
    position: int

class ImageResponse(ImageCreate):
    id: int
    ad_id: int
    url: str
    position: int
    created_at: datetime


class MessageCreate(BaseModel):
    ad_id: int
    sender_id: int
    receiver_id: int
    text: str

class MessageResponse(MessageCreate):
    id: int
    is_read: bool
    created_at: datetime


class FavoriteCreate(BaseModel):
    user_id: int
    ad_id: int

class FavoriteResponse(FavoriteCreate):
    id: int
    created_at: datetime


class CityCreate(BaseModel):
    name: str


class CityResponse(CityCreate):
    id: int
