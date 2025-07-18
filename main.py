import logging
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from app.database.mongo import enterprise_repo
from app.database.mongo.enterprise_repo import Enterprise
from app.util import utils

from fastapi import FastAPI, Request
from app.api import (
    llm_filter,
    utils as utils_api,
    document,
    google,
    json,
    forwarder
)


def create_app() -> FastAPI:
    api = FastAPI(
        title="Multi-Search API",
        version="1.0.0",
        description="Provides LLM.py, Semantic, and Full-text Search APIs.",
    )

    return api

#Test
api = create_app()
api.include_router(llm_filter.router, prefix="/api/v1/filter")
api.include_router(utils_api.router, prefix="/api/v1/utils")
api.include_router(document.router, prefix="/api/v1/document")
api.include_router(google.router, prefix="/api/v1/google")
api.include_router(json.router, prefix="/api/v1/json")
api.include_router(forwarder.router, prefix="/api/v1/forwarder")


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)


@api.middleware("http")
async def api_log_middleware(request: Request, call_next):
    start = utils.current_time_ms()
    method = request.method
    logger.info(f"[{method.upper()}] {request.url}")
    response = await call_next(request)
    response.headers['X-Process-Time'] = str(utils.current_time_ms() - start)
    return response

if __name__ == "__main__":
    # enterprise = enterprise_repo.get_enterprise('6502bfaea7cc3b4bcb61c7a6')
    # print(enterprise)
    import uvicorn

    uvicorn.run(api, host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=False)
    sys.exit(0)
