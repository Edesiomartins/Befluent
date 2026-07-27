from pydantic import BaseModel, ConfigDict, Field
class ORM(BaseModel): model_config=ConfigDict(from_attributes=True)
class LoginIn(BaseModel): email:str; password:str
class LanguageActivate(BaseModel): code:str
class OnboardingIn(BaseModel): language_code:str; level_estimate:str|None=None; goals:list[str]=[]
class TextIn(BaseModel): text:str=Field(min_length=1,max_length=5000)
class VocabularyIn(BaseModel): language_code:str; term:str; translation_pt:str; reading_or_pinyin:str|None=None; notes:str|None=None
class VocabularyUpdate(BaseModel): translation_pt:str|None=None; reading_or_pinyin:str|None=None; notes:str|None=None; status:str|None=None
class ReviewAnswer(BaseModel): rating:str
class SettingsIn(BaseModel): tts_speed:float|None=Field(None,ge=0.5,le=2); ui_prefs:dict|None=None; default_language_code:str|None=None
