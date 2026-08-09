import os
from fastapi import FastAPI, Depends, HTTPException
from .database import engine, SessionLocal
from sqlalchemy.orm import Session
from typing import Annotated, Dict, Optional, Any, List
from app import models, schemas
from sqlalchemy import text
from app.utils import hash_password
import json
from fastapi.staticfiles import StaticFiles
from fastapi import File, UploadFile
import shutil
import uuid

from .models import Advertisement

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

#CITIES

os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@app.post("/cities/", response_model=schemas.CityResponse)
def create_city(city: schemas.CityCreate, db: Session = Depends(get_db)):
    check = db.execute(
        text("SELECT id FROM cities WHERE name = :name"),
        {"name": city.name}
    ).fetchone()
    if check:
        raise HTTPException(status_code=400, detail="City already exists")

    result = db.execute(
        text("INSERT INTO cities (name) VALUES (:name) RETURNING id, name"),
        {"name": city.name}
    )
    db.commit()
    row = result.fetchone()
    return {"id": row.id, "name": row.name}


@app.get("/cities/{id}", response_model=List[schemas.CityResponse])
def get_cities_list(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id, name FROM cities ORDER BY id OFFSET :skip LIMIT :limit"),
        {"skip": skip, "limit": limit}).fetchall()
    return [{"id": row.id, "name": row.name} for row in rows]


@app.get("/cities/{city_id}", response_model=schemas.CityResponse)
def get_city(city_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT id, name FROM cities WHERE id = :id"),
        {"id": city_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="City not found")
    return {"id": row.id, "name": row.name}


@app.put("/cities/{city_id}", response_model=schemas.CityResponse)
def update_city(city_id: int, city: schemas.CityCreate, db: Session = Depends(get_db)):
    row = db.execute(
        text("UPDATE cities SET name = :name WHERE id = :id"),
        {"id": city_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="City not found")

    result = db.execute(
        text("UPDATE cities SET name = :name WHERE id = :id RETURNING id, name"),
        {"name": city.name, "id": city.id})
    db.commit()
    updated = result.fetchone()
    return {"id": updated.id, "name": updated.name}

@app.delete("/cities/{city_id}")
def delete_city(city_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text("DELETE FROM cities WHERE id = :id RETURNING id"),
        {"id": city_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="City not found")
    return {"message": "City deleted successfully"}


##################################



#CATEGORIES


@app.post("/categories/", response_model=schemas.CategoryResponse)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    check = db.execute(text("SELECT id FROM categories WHERE name = :name OR slug = :slug"),
        {"name": category.name, "slug": category.slug}
    ).fetchone()
    if check:
        raise HTTPException(status_code=400, detail="Category already exists")
    if category.parent_category_id is not None:
        parent = db.execute(
            text("SELECT level FROM categories WHERE id = :pid"),
            {"pid": category.parent_category_id}
        ).fetchone()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")
        level = parent.level + 1
    else:
        level = 0


    result = db.execute(
        text("""INSERT INTO categories (name, slug, parent_category_id, level)
             VALUES (:name, :slug, :parent_category_id, :level)
             RETURNING id, name, slug, parent_category_id, level"""),
        {"name": category.name, "slug": category.slug,
         "parent_category_id": category.parent_category_id, "level": level}
    )
    db.commit()
    row = result.fetchone()
    return {"id": row.id, "name": row.name, "slug": row.slug,
            "parent_category_id": row.parent_category_id, "level": level}


@app.get("/categories/", response_model=schemas.CategoryResponse)
def list_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id, name, slug, parent_category_id, level FROM categories ORDER BY id OFFSET :skip LIMIT :limit"),
        {"skip": skip, "limit": limit}
    ).fetchall()
    return [{"id": row.id, "name": row.name, "slug": row.slug,
             "parent_category_id": row.parent_category_id,
             "level": row.level} for row in rows]

@app.get("/categories/{category_id}", response_model=schemas.CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT id, name, slug, parent_category_id, level FROM categories WHERE id = :id"),
        {"id": category_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"id": row.id, "name": row.name, "slug": row.slug,
            "parent_category_id": row.parent_category_id, "level": row.level}


@app.put("/categories/{category_id}", response_model=schemas.CategoryResponse)
def update_category(category_id: int, category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    check = db.execute(
        text("SELECT id FROM categories WHERE id = :id"),
        {"id": category_id}
    ).fetchone()
    if not check:
        raise HTTPException(status_code=404, detail="Category not found")

    conflict = db.execute(
        text("SELECT id FROM categories WHERE (name = :name OR slug = :slug) AND id != :id"),
        {"name": category.name, "slug": category.slug, "id": category_id}
    ).fetchone()
    if conflict:
        raise HTTPException(status_code=400, detail="Category or slug already exists")


    new_level = 0
    if category.parent_category_id is not None:
        parent = db.execute(
            text("SELECT level FROM categories WHERE id = :parent_category_id"),
            {"parent_category_id": category.parent_category_id}
        ).fetchone()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")
        new_level = parent.level + 1


    result = db.execute(
        text("""UPDATE categories SET name = :name, slug = :slug,
             parent_category_id = :parent_category_id
              WHERE id = :id RETURNING id, name, slug, parent_category_id, level"""),
        {"name": category.name, "slug": category.slug,
         "parent_category_id": category.parent_category_id,
         "level": new_level, "id":category_id}
    )
    db.commit()
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"id": row.id, "name": row.name, "slug": row.slug,
            "parent_category_id": row.parent_category_id, "level": row.level}


@app.delete("/categories/{category_id}", response_model=schemas.CategoryResponse)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    child = db.execute(
        text("SELECT id FROM categories WHERE parent_category_id = :parent_category_id"),
        {"parent_category_id": category_id}
    ).fetchone()
    if child:
        raise HTTPException(status_code=404, detail="Cant delete category with child categories")
    result = db.execute(
        text("DELETE FROM categories WHERE id = :id RETURNING id"),
        {"id": category_id}
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "category deleted successfully"}


#ATTRIBUTES

@app.post("/attributes/", response_model=schemas.AttributeResponse)
def create_attribute(attribute: schemas.AttributeCreate, db: Session = Depends(get_db)):
    category_check = db.execute(
        text("SELECT id FROM categories WHERE id = :category_id"),
        {"category_id": attribute.category_id}
    ).fetchone()
    if not category_check:
        raise HTTPException(status_code=404, detail="Category not found")

    slug_exists = db.execute(
        text("SELECT slug FROM attributes WHERE category_id = :category_id AND slug = :slug"),
        {"category_id": attribute.category_id, "slug": attribute.slug}
    ).fetchone()
    if slug_exists:
        raise HTTPException(status_code=400, detail="Attribute with this slug already exists")

    result = db.execute(
        text("""INSERT INTO attributes (category_id, name, slug,
         data_type, is_filterable, unit) 
         VALUES (:category_id, :name, :slug, :data_type, :is_filterable, :unit) 
         RETURNING id, category_id, name, slug, data_type, is_filterable, unit"""),
        {
            "category_id": attribute.category_id,
            "name": attribute.name,
            "slug": attribute.slug,
            "data_type": attribute.data_type,
            "is_filterable": attribute.is_filterable,
            "unit": attribute.unit
        }
    )
    db.commit()
    row = result.fetchone()
    return {
        "id": row.id,
        "category_id": row.category_id,
        "name": row.name,
        "slug": row.slug,
        "data_type": row.data_type,
        "is_filterable": row.is_filterable,
        "unit": row.unit
    }

@app.get("/attributes/", response_model=schemas.AttributeResponse)
def get_attributes_list(skip: int = 0, limit: int = 100, category_id: Optional[int] = None, db: Session = Depends(get_db)):
    if category_id is not None:
        rows = db.execute(
            text("""SELECT id, category_id, name, slug, data_type, is_filterable, unit
            FROM attributes WHERE category_id = :category_id ORDER BY id
            OFFSET :skip LIMIT :limit"""),
            {"category_id": category_id, "skip": skip, "limit": limit}
        ).fetchall()
    else:
        rows = db.execute(
            text("""SELECT id, category_id, name, slug, data_type, is_filterable, unit
            FROM attributes ORDER BY id
            OFFSET :skip LIMIT :limit"""),
            {"skip": skip, "limit": limit}
        ).fetchall()
    return [{"id": row.id,
             "category_id": row.category_id,
             "name": row.name,
             "slug": row.slug,
             "data_type": row.data_type,
             "is_filterable": row.is_filterable,
             "unit": row.unit} for row in rows]


@app.get("/attributes/{attribute_id}", response_model=schemas.AttributeResponse)
def get_attribute(attribute_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        text("""
            SELECT id, category_id, name, slug, data_type, is_filterable, unit
            FROM attributes
            WHERE id = :id
        """),
        {"id": attribute_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Attribute not found")
    return {
        "id": row.id,
        "category_id": row.category_id,
        "name": row.name,
        "slug": row.slug,
        "data_type": row.data_type,
        "is_filterable": row.is_filterable,
        "unit": row.unit
    }


@app.put("/attributes/{attribute_id}", response_model=schemas.AttributeResponse)
def update_attribute(attribute_id: int, attr: schemas.AttributeCreate, db: Session = Depends(get_db)):
    # Проверяем, что атрибут существует
    existing = db.execute(
        text("SELECT id FROM attributes WHERE id = :id"),
        {"id": attribute_id}
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Attribute not found")

    # Проверяем, что категория, на которую обновляем, существует
    category = db.execute(
        text("SELECT id FROM categories WHERE id = :cid"),
        {"cid": attr.category_id}
    ).fetchone()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Проверяем, что новый slug не занят другим атрибутом в этой же категории
    conflict = db.execute(
        text("""
            SELECT id FROM attributes
            WHERE category_id = :cid AND slug = :slug AND id != :id
        """),
        {"cid": attr.category_id, "slug": attr.slug, "id": attribute_id}
    ).fetchone()
    if conflict:
        raise HTTPException(status_code=400, detail="Another attribute with this slug already exists in this category")

    # Обновление
    result = db.execute(
        text("""
            UPDATE attributes
            SET category_id = :cid,
                name = :name,
                slug = :slug,
                data_type = :dtype,
                is_filterable = :filterable,
                unit = :unit
            WHERE id = :id
            RETURNING id, category_id, name, slug, data_type, is_filterable, unit
        """),
        {
            "cid": attr.category_id,
            "name": attr.name,
            "slug": attr.slug,
            "dtype": attr.data_type,
            "filterable": attr.is_filterable,
            "unit": attr.unit,
            "id": attribute_id
        }
    )
    db.commit()
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Attribute not found")
    return {
        "id": row.id,
        "category_id": row.category_id,
        "name": row.name,
        "slug": row.slug,
        "data_type": row.data_type,
        "is_filterable": row.is_filterable,
        "unit": row.unit
    }


@app.delete("/attributes/{attribute_id}")
def delete_attribute(attribute_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text("DELETE FROM attributes WHERE id = :id RETURNING id"),
        {"id": attribute_id}
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Attribute not found")
    return {"message": "Attribute deleted"}


###################



#USERS


@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    email_exist = db.execute(
        text("SELECT email FROM users WHERE email = :email"),
        {"email": user.email}
    ).fetchone()
    if email_exist:
        raise HTTPException(status_code=400, detail="Email already taken")


    hashed = hash_password(user.password)

#TODO как проверки делать за один запрос правильно

    result = db.execute(
        text("""INSERT INTO users (email, phone, password_hash, name, avatar_url) 
        VALUES (:email, :phone, :password_hash, :name, :avatar_url)
        RETURNING id, email, phone, password_hash, name, avatar_url, rating, registration_date"""),
        {"email": user.email,
                "phone": user.phone,
                "password_hash": hashed,
               "name": user.name,
         "avatar_url": user.avatar_url
         }
    )
    db.commit()
    row = result.fetchone()
    return {
        "id": row.id,
        "email": row.email,
        "phone": row.phone,
        "name": row.name,
        "avatar_url": row.avatar_url,
        "rating": float(row.rating) if row.rating else 0.0,
        "registration_date": row.registration_date
    }


@app.get("/users/", response_model=List[schemas.UserResponse])
def get_users_list(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    rows = db.execute(
        text("""
            SELECT id, email, phone, name, avatar_url, rating, registration_date
            FROM users
            ORDER BY id
            OFFSET :skip LIMIT :limit
        """),
        {"skip": skip, "limit": limit}
    ).fetchall()
    return [
        schemas.UserResponse(
            id=r.id,
            email=r.email,
            phone=r.phone,
            name=r.name,
            avatar_url=r.avatar_url,
            rating=float(r.rating) if r.rating is not None else 0.0,
            registration_date=r.registration_date
        )
        for r in rows
    ]

@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):

    row = db.execute(
        text("""SELECT id, email, phone, password_hash, name, avatar_url, rating, registration_date
        FROM users WHERE id = :id"""),
        {"id": user_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": row.id,
        "email": row.email,
        "phone": row.phone,
        "name": row.name,
        "avatar_url": row.avatar_url,
        "rating": float(row.rating) if row.rating else 0.0,
        "registration_date": row.registration_date
    }

@app.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, user: schemas.UserCreate, db: Session = Depends(get_db)):
    user_exist = db.execute(
        text("SELECT id FROM users WHERE id = :id"),
        {"id": user_id}
    ).fetchone()

    if not user_exist:
        raise HTTPException(status_code=404, detail="User not found")

    email_conflict = db.execute(
        text("SELECT id FROM users WHERE email = :email AND id != :id"),
        {"email": user.email, "id": user_id}
    ).fetchone()

    if email_conflict:
        raise HTTPException(status_code=400, detail="Email already taken")

    hashed = hash_password(user.password)
    result = db.execute(
        text("""UPDATE users 
        SET email = :email, phone = :phone, password_hash = :password_hash, 
        name = :name, avatar_url = :avatar_url
        WHERE id = :id
        RETURNING id, email, phone, name, avatar_url, rating, registration_date"""
    ),
        {"email": user.email,
         "phone": user.phone,
         "password_hash": hashed,
         "name": user.name,
         "avatar_url": user.avatar_url,
         "id": user_id}
    )
    db.commit()

    row = result.fetchone()

    return {
        "id": row.id,
        "email": row.email,
        "phone": row.phone,
        "name": row.name,
        "avatar_url": row.avatar_url,
        "rating": float(row.rating) if row.rating else 0.0,
        "registration_date": row.registration_date
    }


@app.delete("/users/{user_id}", response_model=schemas.UserResponse)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text("""DELETE FROM users WHERE id = :id"""),
        {"id": user_id}
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "user deleted"}



#### ОБЪЯВЛЕНИЯ

@app.post('/advertisements/', response_model=schemas.AdvertisementResponse)
def create_advertisement(ads: schemas.AdvertisementCreate, db: Session = Depends(get_db)):

    user_exist = db.execute(
        text("SELECT id FROM users WHERE id = :ads_user_id"),
        {'ads_user_id': ads.user_id}
    ).fetchone()

    if not user_exist:
        raise HTTPException(status_code=404, detail="User not found")


    category_check = db.execute(
        text("SELECT id FROM categories WHERE id = :category_id"),
        {'category_id': ads.category_id}
    ).fetchone()
    if not category_check:
        raise HTTPException(status_code=404, detail="Category not found")


    city_check = db.execute(
        text("SELECT id FROM cities WHERE id = :city_id"),
        {'city_id': ads.city}
    ).fetchone()

    if not city_check:
        raise HTTPException(status_code=404, detail="City not found")

    params_json = json.dumps(ads.params)

    result = db.execute(
        text("""
        INSERT INTO ads (user_id, category_id, title, description, price, status, city, address, params, views_count)
        VALUES (:user_id, :category_id, :title, :description, :price, :status, :city, :address, :params, 0)
        RETURNING id, user_id, category_id, title, description, price, status, city, address, params, views_count, created_at, updated_at"""
    ),{
        "user_id": ads.user_id,
        "category_id": ads.category_id,
        "title": ads.title,
        "description": ads.description,
        "price": ads.price,
        "status": ads.status,
        "city": ads.city,
        "address": ads.address,
        "params": params_json}
    )


    db.commit()

    row = result.fetchone()
    return {
        "id": row.id,
        "user_id": row.user_id,
        "category_id": row.category_id,
        "title": row.title,
        "description": row.description,
        "price": row.price,
        "status": row.status,
        "city": row.city,
        "address": row.address,
        "params": row.params,
        "views_count": row.views_count,
        "created_at": row.created_at,
        "updated_at": row.updated_at
    }


@app.get('/ads/, response_model=schemas.AdvertisementResponse')
def get_advertisement(skip: int = 0,
    limit: int = 20,
    category_id: Optional[int] = None,
    city_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    status: Optional[str] = "active",
    search: Optional[str] = None, db: Session = Depends(get_db)):

    query = """SELECT id, user_id, category_id, title, description, price, status, city, address, params, views_count, created_at, updated_at 
    FROM ads WHERE 1=1"""

    params = {}

    if status is not None:
        query += " AND status = :status"
        params["status"] = status

    if category_id is not None:
        query += " AND category_id = :category_id"
        params["category_id"] = category_id

    if city_id is not None:
        query += " AND city_id = :city_id"
        params["city_id"] = city_id

    if min_price is not None:
        query += " AND price < :min_price"
        params["min_price"] = min_price

    if max_price is not None:
        query += " AND price > :max_price"
        params["max_price"] = max_price

    if search is not None:
        query += " AND search = :search"
        params["search"] = search

    query += " ORDER BY created_at DESC OFFSET :skip LIMIT :limit"
    params["skip"] = skip
    params["limit"] = limit

    rows = db.execute(text(query), params).fetchall()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "category_id": r.category_id,
            "title": r.title,
            "description": r.description,
            "price": r.price,
            "status": r.status,
            "city": r.city,
            "address": r.address,
            "params": r.params,
            "views_count": r.views_count,
            "created_at": r.created_at,
            "updated_at": r.updated_at
        }
        for r in rows
    ]


@app.put("/ads/{ad_id}", response_model=schemas.AdvertisementResponse)
def edit_advertisement(ad_id: int, ad: schemas.AdvertisementCreate, db: Session = Depends(get_db)):
    ad_exists = db.execute(text("SELECT id FROM ads WHERE id = :id"),{"id": ad_id}).fetchone()
    if not ad_exists:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    user_exists = db.execute(text("SELECT id FROM users WHERE id = :user_id"),{"user_id": ad.user_id}).fetchone()
    if not user_exists:
        raise HTTPException(status_code=404, detail="User not found")

    category_exists = db.execute(text("SELECT id FROM categories WHERE id = :category_id"), {"category_id": ad.category_id}).fetchone()
    if not category_exists:
        raise HTTPException(status_code=404, detail="Category not found")

    city_exists = db.execute(text("SELECT id FROM cities WHERE id = :city_id"), {"city_id": ad.city}).fetchone()
    if not city_exists:
        raise HTTPException(status_code=404, detail="City not found")

    result = db.execute(
        text("""
        UPDATE ads SET user_id = :user_id, category_id = :category_id, 
        title = :title, description = :description, price = :price, status = :status, city = :city, 
        address = :address, params = :params 
        WHERE id = :id RETURNING id, user_id, category_id, title, description, price, status, city, 
        address, params, views_count, created_at, updated_at"""),
        {
            "user_id": ad.user_id,
            "category_id": ad.category_id,
            "title": ad.title,
            "description": ad.description,
            "price": ad.price,
            "status": ad.status,
            "city": ad.city,
            "address": ad.address,
            "params": ad.params,
            "id": ad_id
        }).fetchall()
    db.commit()

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    return {
        "id": row.id,
        "user_id": row.user_id,
        "category_id": row.category_id,
        "title": row.title,
        "description": row.description,
        "price": row.price,
        "status": row.status,
        "city": row.city,
        "address": row.address,
        "params": row.params,
        "views_count": row.views_count,
        "created_at": row.created_at,
        "updated_at": row.updated_at
    }


@app.delete("/ads/{ad_id}")
def delete_advertisement(ad_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text("DELETE FROM ads WHERE id = :id RETURNING id"), {"id": ad_id}
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    return {
        "message": "Advertisement deelted succsessfully"
    }




### ИЗБРАННОЕ



@app.post("/favorites/", response_model=schemas.FavoriteResponse)
def add_favorite(favorite: schemas.FavoriteCreate, db: Session = Depends(get_db)):

    user_check = db.execute(
        text("SELECT id FROM users WHERE id = :user_id"),
        {"user_id": favorite.user_id}
    ).fetchone()
    if not user_check:
        raise HTTPException(status_code=404, detail="User not found")

    ad_exists = db.execute(
        text("SELECT id FROM ads WHERE id = :ad_id"),
        {"ad_id": favorite.ad_id}
    ).fetchone()

    if not ad_exists:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    result = db.execute(
        text("""INSERT INTO favorites (user_id, ad_id) VALUES (:user_id, :ad_id) RETURNING id, user_id, ad_id, created_at"""),
        {"user_id": favorite.user_id, "ad_id": favorite.ad_id}

    )

    db.commit()
    row = result.fetchone()
    return {
        "id": row.id,
        "user_id": row.user_id,
        "ad_id": row.ad_id,
        "created_at": row.created_at
    }


@app.get("/favorites/", response_model=List[schemas.FavoriteResponse])
def get_favorites(user_id: int, skip: int=0, limit: int=100,db: Session = Depends(get_db)):
    rows = db.execute(
        text("""SELECT id, user_id, ad_id, created_at
        FROM favorites
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        OFFSET :skip LIMIT :limit"""),
        {"user_id": user_id, "skip": skip, "limit": limit}
    ).fetchall()

    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "ad_id": row.ad_id,
            "created_at": row.created_at
        }
        for row in rows
    ]



@app.delete("/favorites/{favorite_id}")
def delete_favorite(favorite_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text("DELETE FROM favorites WHERE id = :id RETURNING id"),
        {"id": favorite_id}
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"message": "Favorite deleted successfully"}


### ИЗОБРАЭЕНИЯ



@app.post("/ads/{ad_id}/images/", response_model=List[schemas.ImageResponse])
async def upload_images(
        ad_id: int, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):


    ad_exists = db.execute(
        text("SELECT id FROM ads WHERE id = :ad_id"),
        {"ad_id": ad_id}
    ).fetchone()
    if not ad_exists:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    max_order = db.execute(
        text("SELECT COALESCE(MAX(position), -1) FROM images WHERE ad_id = :ad_id"),
        {"ad_id": ad_id}
    ).scalar()


    created_images = []
    for index, file in enumerate(files):



        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = f"static/images/{filename}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        position = max_order + index + 1
        result = db.execute(
            text("INSERT INTO images (ad_id, url, position) VALUES (:ad_id, :url, :position) RETURNING id, ad_id, url, position, created_at"),
         {"ad_id": ad_id, "url": f"/static/images/{filename}", "position": position})
        db.commit()
        row = result.fetchone()
        created_images.append({
            "id": row.id,
            "ad_id": row.ad_id,
            "url": row.url,
            "position": row.position,
            "created_at": row.created_at

        })

    return created_images



@app.get("/ads/{ad_id}/images/", response_model=List[schemas.ImageResponse])
def get_images(ad_id: int, db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id, ad_id, url, position, created_at FROM images WHERE ad_id = :ad_id ORDER BY position"),
    {"ad_id": ad_id}).fetchall()
    return [
        {
            "id": row.id,
            "ad_id": row.ad_id,
            "url": row.url,
            "position": row.position,
            "created_at": row.created_at
        }
        for row in rows
    ]


@app.delete("/images/{image_id}", response_model=schemas.ImageResponse)
def delete_image(ad_id: int, image_id: int, db: Session = Depends(get_db)):

    row = db.execute(
        text("SELECT id, ad_id, url, position, created_at FROM images WHERE id = :id"),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = row.url.lstrip('/')
    if os.path.exists(file_path):
        os.remove(file_path)

    db.execute(
        text("DELETE FROM images WHERE id = :id"),
        {"id": image_id}
    )

    db.commit()
    return {"message": "Image deleted successfully"}