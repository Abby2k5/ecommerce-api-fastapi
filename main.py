from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from database import SessionLocal, engine
import models

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.middleware("http")
async def log_requests(request: Request, call_next):

    response = await call_next(request)

    with open("requests.log", "a") as log_file:
        log_file.write(
            f"{datetime.now()} | "
            f"{request.method} | "
            f"{request.url.path} | "
            f"{response.status_code}\n"
        )

    return response


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


class Product(BaseModel):
    name: str
    price: float


class User(BaseModel):
    username: str
    password: str


@app.get("/")
def root():
    return {"message": "E-Commerce API Running"}


@app.get("/products")
def get_products(db: Session = Depends(get_db)):

    products = db.query(models.ProductDB).all()

    return products


@app.post("/products")
def create_product(
    product: Product,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    new_product = models.ProductDB(
        name=product.name,
        price=product.price
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return {
        "message": "Product added",
        "product": new_product
    }


@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    updated_product: Product,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    product = db.query(models.ProductDB).filter(
        models.ProductDB.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    product.name = updated_product.name
    product.price = updated_product.price

    db.commit()
    db.refresh(product)

    return {
        "message": "Product updated",
        "product": product
    }


@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    product = db.query(models.ProductDB).filter(
        models.ProductDB.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    db.delete(product)
    db.commit()

    return {
        "message": "Product deleted",
        "product": product
    }


@app.post("/register")
def register(user: User, db: Session = Depends(get_db)):

    existing_user = db.query(models.UserDB).filter(
        models.UserDB.username == user.username
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    hashed_pw = hash_password(user.password)

    new_user = models.UserDB(
        username=user.username,
        password=hashed_pw
    )

    db.add(new_user)
    db.commit()

    return {
        "message": "User registered successfully"
    }


@app.post("/login")
def login(user: User, db: Session = Depends(get_db)):

    db_user = db.query(models.UserDB).filter(
        models.UserDB.username == user.username
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not verify_password(user.password, db_user.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    token = create_access_token(
        data={"sub": db_user.username}
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }