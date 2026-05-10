from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from database import SessionLocal, engine
import models

from auth import (
    hash_password,
    verify_password,
    create_access_token
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


# REQUEST LOGGING
@app.middleware("http")
async def log_requests(request: Request, call_next):

    response = await call_next(request)

    log = f"{datetime.now()} | {request.method} | {request.url.path} | {response.status_code}\n"

    with open("requests.log", "a") as file:
        file.write(log)

    return response


# DATABASE CONNECTION
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# PRODUCT SCHEMA
class Product(BaseModel):
    name: str
    price: float


# USER SCHEMA
class User(BaseModel):
    username: str
    password: str


# ROOT
@app.get("/")
def root():
    return {"message": "API is working"}


# GET PRODUCTS
@app.get("/products")
def get_products(db: Session = Depends(get_db)):

    products = db.query(models.ProductDB).all()

    return products


# CREATE PRODUCT
@app.post("/products")
def create_product(product: Product, db: Session = Depends(get_db)):

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


# UPDATE PRODUCT
@app.put("/products/{product_id}")
def update_product(product_id: int, product: Product, db: Session = Depends(get_db)):

    existing_product = db.query(models.ProductDB).filter(
        models.ProductDB.id == product_id
    ).first()

    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")

    existing_product.name = product.name
    existing_product.price = product.price

    db.commit()

    return {
        "message": "Product updated",
        "product": existing_product
    }


# DELETE PRODUCT
@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):

    product = db.query(models.ProductDB).filter(
        models.ProductDB.id == product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()

    return {
        "message": "Product deleted",
        "product": product
    }


# REGISTER
@app.post("/register")
def register(user: User, db: Session = Depends(get_db)):

    existing_user = db.query(models.UserDB).filter(
        models.UserDB.username == user.username
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

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


# LOGIN
@app.post("/login")
def login(user: User, db: Session = Depends(get_db)):

    existing_user = db.query(models.UserDB).filter(
        models.UserDB.username == user.username
    ).first()

    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(user.password, existing_user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(
        data={"sub": existing_user.username}
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }