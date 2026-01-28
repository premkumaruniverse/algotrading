from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    # Kite Credentials
    api_key = Column(String, nullable=True)
    api_secret = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    request_token_updated_at = Column(DateTime, nullable=True)
    
    # Trading Configuration
    is_trading_active = Column(Boolean, default=False)
    num_lots = Column(Integer, default=1)
    
    trades = relationship("Trade", back_populates="owner")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    symbol = Column(String)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime, nullable=True)
    
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    
    quantity = Column(Integer)
    pnl = Column(Float, nullable=True)
    status = Column(String) # OPEN, CLOSED
    reason = Column(String, nullable=True)
    
    owner = relationship("User", back_populates="trades")
