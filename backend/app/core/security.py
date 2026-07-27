import hashlib, secrets
from passlib.context import CryptContext
pwd=CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_password(value:str)->str: return pwd.hash(value)
def verify_password(value:str, hashed:str)->bool: return pwd.verify(value, hashed)
def new_token()->str: return secrets.token_urlsafe(48)
def token_hash(value:str)->str: return hashlib.sha256(value.encode()).hexdigest()
