from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Numeric, JSON, func, Index
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True,  index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    password_hash = Column(String(255))
    name = Column(String(100), nullable=False)
    avatar_url = Column(String, nullable=True)
    rating = Column(Float, nullable=False, server_default="0.0")
    registration_date = Column(DateTime, server_default=func.now())



class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True) #сделал уникальными шобы не было путаницы
    slug = Column(String, unique=True, index=True)
    parent_category_id = Column(Integer, ForeignKey("categories.id"), index=True)
    level = Column(Integer)


class Attribute(Base):
    __tablename__ = "attributes"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), index=True)
    name = Column(String, nullable=False)
    slug = Column(String, index=True)
    data_type = Column(String, index=True, nullable=False)
    is_filterable = Column(Boolean, index=True)
    unit = Column(String, index=True) #единица измерения


class Advertisement(Base):
    __tablename__ = "ads"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    title = Column(String(255), index=True)
    description = Column(String, nullable=True)
    price = Column(Integer, nullable=False)
    status = Column(String, default="draft", index=True)
    city = Column(Integer, ForeignKey("cities.id"), nullable=False, index=True)
    address = Column(String, nullable=True, index=True)
    views_count = Column(Integer, default=0)
    params = Column(JSONB, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_ads_category_status', 'category_id', 'status'),
        Index('idx_ads_price', 'price'),
        Index('idx_ads_params', 'params', postgresql_using='gin'),
    )


class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True)
    ad_id = Column(Integer, ForeignKey("ads.id"), index=True)
    url = Column(String)
    position = Column(Integer) #порядок отображения пикчи в объяве
    created_at = Column(DateTime, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    ad_id = Column(Integer, ForeignKey("ads.id"), index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), index=True)
    text = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    ad_id = Column(Integer, ForeignKey("ads.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())


class City(Base):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)