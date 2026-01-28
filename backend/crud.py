from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_credentials(db: Session, user_id: int, api_key: str, api_secret: str, num_lots: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.api_key = api_key
        user.api_secret = api_secret
        user.num_lots = num_lots
        db.commit()
        db.refresh(user)
    return user

def update_user_token(db: Session, user_id: int, access_token: str):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.access_token = access_token
        from datetime import datetime
        user.request_token_updated_at = datetime.now()
        db.commit()
        db.refresh(user)
    return user

def toggle_trading(db: Session, user_id: int, status: bool):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.is_trading_active = status
        db.commit()
        db.refresh(user)
    return user

def create_trade(db: Session, trade: schemas.TradeCreate, user_id: int):
    from datetime import datetime
    db_trade = models.Trade(**trade.dict(), user_id=user_id, entry_time=datetime.now())
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

def close_trade(db: Session, trade_id: int, exit_price: float, reason: str):
    trade = db.query(models.Trade).filter(models.Trade.id == trade_id).first()
    if trade:
        from datetime import datetime
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.status = "CLOSED"
        trade.reason = reason
        trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
        db.commit()
        db.refresh(trade)
    return trade

def get_user_trades(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Trade).filter(models.Trade.user_id == user_id).order_by(models.Trade.entry_time.desc()).offset(skip).limit(limit).all()

def get_open_trades(db: Session, user_id: int):
    return db.query(models.Trade).filter(models.Trade.user_id == user_id, models.Trade.status == "OPEN").all()
