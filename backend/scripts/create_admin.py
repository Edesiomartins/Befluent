import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import func,select
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User,UserPreference
def main():
    email=os.getenv("INITIAL_ADMIN_EMAIL","").strip().lower(); password=os.getenv("INITIAL_ADMIN_PASSWORD",""); name=os.getenv("INITIAL_ADMIN_NAME","Administrador").strip()
    if not email or not password: raise SystemExit("Defina INITIAL_ADMIN_EMAIL e INITIAL_ADMIN_PASSWORD.")
    if len(password)<8: raise SystemExit("INITIAL_ADMIN_PASSWORD deve ter pelo menos 8 caracteres.")
    with SessionLocal() as db:
        existing=db.scalar(select(User).where(User.email==email))
        if existing: print("Administrador já existe; nenhuma alteração feita."); return
        if (db.scalar(select(func.count(User.id))) or 0)>0: raise SystemExit("Já existe um usuário. A criação de um segundo usuário foi recusada.")
        user=User(email=email,password_hash=hash_password(password),name=name); db.add(user); db.flush(); db.add(UserPreference(user_id=user.id)); db.commit()
        print("Administrador criado com sucesso.")
if __name__=="__main__": main()
