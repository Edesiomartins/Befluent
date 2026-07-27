from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Language
LANGUAGES=[
("en","Inglês","English","Inglês internacional","Ênfase em conversação, escuta e vocabulário frequente."),
("es-ES","Espanhol da Espanha","Español","Variante da Espanha","Ênfase no espanhol europeu, vosotros, pronúncia e uso cotidiano."),
("fr","Francês","Français","Francês padrão","Ênfase em compreensão oral, liaison e comunicação prática."),
("ja","Japonês","日本語","Japonês padrão","Progressão por escrita, partículas, escuta e níveis de formalidade."),
("zh-CN","Mandarim","中文","Mandarim simplificado","Ênfase em tons, pinyin, caracteres simplificados e comunicação."),
]
def seed_languages(db:Session):
    for code,name,native,desc,strategy in LANGUAGES:
        if not db.scalar(select(Language).where(Language.code==code)):
            db.add(Language(code=code,name_pt=name,native_name=native,variant_note=desc,description=desc,strategy_summary=strategy))
    db.commit()
