from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.errors import error_payload
SAFE={"GET","HEAD","OPTIONS"}
EXEMPT={"/api/v1/auth/login"}
async def csrf_guard(request:Request, call_next):
    if request.method not in SAFE and request.url.path not in EXEMPT:
        cookie=request.cookies.get("csrf_token"); header=request.headers.get("X-CSRF-Token")
        if not cookie or not header or cookie!=header:
            return JSONResponse(
                status_code=403,
                content=error_payload(request,"csrf_invalid","Token CSRF ausente ou inválido."),
            )
    return await call_next(request)
