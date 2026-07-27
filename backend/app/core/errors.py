from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
class APIError(Exception):
    def __init__(self, status_code:int, code:str, message:str, retryable:bool=False):
        self.status_code=status_code; self.code=code; self.message=message; self.retryable=retryable
def error_payload(request:Request, code:str, message:str, retryable=False):
    return {"error":{"code":code,"message":message,"retryable":retryable,"request_id":getattr(request.state,"request_id","unknown")}}
async def api_error_handler(request:Request, exc:APIError):
    return JSONResponse(status_code=exc.status_code, content=error_payload(request,exc.code,exc.message,exc.retryable))
async def validation_error_handler(request:Request, exc):
    return JSONResponse(status_code=422, content=error_payload(request,"validation_error","Dados enviados são inválidos."))
async def http_error_handler(request:Request, exc:HTTPException):
    messages={404:"Recurso não encontrado.",405:"Método não permitido."}
    message=messages.get(exc.status_code,"Não foi possível concluir a solicitação.")
    return JSONResponse(status_code=exc.status_code,content=error_payload(request,"http_error",message))
async def unexpected_error_handler(request:Request, exc:Exception):
    return JSONResponse(status_code=500,content=error_payload(request,"internal_error","Erro interno do servidor.",True))
