from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TradeBase(BaseModel):
    symbol: str
    entry_price: float
    quantity: int
    status: str

class TradeCreate(TradeBase):
    pass

class Trade(TradeBase):
    id: int
    user_id: int
    entry_time: datetime
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    reason: Optional[str] = None

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    num_lots: Optional[int] = None
    is_trading_active: Optional[bool] = None

class TokenUpdate(BaseModel):
    request_token: str

class User(UserBase):
    id: int
    is_trading_active: bool
    num_lots: int
    trades: List[Trade] = []
    api_key: Optional[str] = None # Should probably hide this in real app, but ok for now
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
