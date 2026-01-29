from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from . import crud, models, schemas, database, trading_engine
from .database import engine
from kiteconnect import KiteConnect
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import uvicorn
import logging

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your ALB DNS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Scheduler for Trading Engine
scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))
engine_instance = trading_engine.TradingEngine()

# Run strategy every 1 minute (For testing, maybe 5 min in prod)
scheduler.add_job(engine_instance.run_strategy, 'interval', minutes=1)
scheduler.start()

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/register", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.post("/api/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not crud.pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Simplified token (just returning username as token for prototype, use JWT in prod)
    # To keep it simple and dependency light, I'll use a dummy JWT-like implementation or just the username if user is okay.
    # But let's do it properly-ish.
    return {"access_token": user.username, "token_type": "bearer"}

def get_current_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl="api/token")), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@app.get("/api/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.post("/api/update_credentials")
def update_credentials(
    api_key: str, 
    api_secret: str, 
    num_lots: int, 
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    return crud.update_user_credentials(db, current_user.id, api_key, api_secret, num_lots)

@app.post("/api/generate_token")
def generate_token(
    request_token: str, 
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.api_key or not current_user.api_secret:
        raise HTTPException(status_code=400, detail="API Key and Secret must be set first")
    
    try:
        kite = KiteConnect(api_key=current_user.api_key)
        data = kite.generate_session(request_token, api_secret=current_user.api_secret)
        access_token = data["access_token"]
        crud.update_user_token(db, current_user.id, access_token)
        return {"status": "success", "access_token": access_token}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/toggle_trading")
def toggle_trading_endpoint(
    status: bool, 
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    return crud.toggle_trading(db, current_user.id, status)

@app.get("/api/trades", response_model=list[schemas.Trade])
def get_trades(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.get_user_trades(db, current_user.id)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
