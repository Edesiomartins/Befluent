import uuid
from fastapi import FastAPI,Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from app.api import assessments,auth,conversations,curriculum,dashboard,grammar,language_profiles,languages,learning_plans,lessons,levels,listening,onboarding,placement_tests,profile,progress,pronunciation,reviews,settings,speech,study_sessions,teaching,tts_lab,tutor_chat,vocabulary,writing
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.csrf import csrf_guard
from app.core.errors import APIError,api_error_handler,http_error_handler,unexpected_error_handler,validation_error_handler
from app.core.logging import configure_logging
configure_logging(); s=get_settings()
_is_prod = str(s.environment).lower() in {"production", "prod"}
app=FastAPI(
    title=s.app_name,
    version="0.1.0",
    docs_url=None if _is_prod and not s.debug else "/docs",
    redoc_url=None if _is_prod and not s.debug else "/redoc",
    openapi_url=None if _is_prod and not s.debug else "/openapi.json",
)
app.add_middleware(CORSMiddleware,allow_origins=[s.frontend_origin],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.exception_handler(APIError)(api_error_handler); app.exception_handler(RequestValidationError)(validation_error_handler)
app.exception_handler(HTTPException)(http_error_handler); app.exception_handler(Exception)(unexpected_error_handler)
@app.middleware("http")
async def request_context(request:Request,call_next):
    request.state.request_id=request.headers.get("X-Request-ID",str(uuid.uuid4()))
    response=await call_next(request); response.headers["X-Request-ID"]=request.state.request_id; return response
@app.middleware("http")
async def security_headers(request:Request,call_next):
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="same-origin"
    if _is_prod:
        response.headers["Strict-Transport-Security"]="max-age=63072000; includeSubDomains"
    return response
app.middleware("http")(csrf_guard)
app.include_router(health_router)
for router in [auth.router,profile.router,languages.router,levels.router,onboarding.router,dashboard.router,placement_tests.router,language_profiles.router,assessments.router,curriculum.router,learning_plans.router,lessons.router,study_sessions.router,conversations.router,speech.router,vocabulary.router,reviews.router,grammar.router,listening.router,pronunciation.router,writing.router,progress.router,settings.router,teaching.router,tutor_chat.router,tts_lab.router]:
    app.include_router(router,prefix="/api/v1")
