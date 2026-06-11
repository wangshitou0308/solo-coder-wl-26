from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.deceased import router as deceased_router
from app.api.v1.transport import router as transport_router
from app.api.v1.farewell import router as farewell_router
from app.api.v1.cremation import router as cremation_router
from app.api.v1.product import router as product_router
from app.api.v1.billing import router as billing_router
from app.api.v1.dashboard import router as dashboard_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(deceased_router)
api_router.include_router(transport_router)
api_router.include_router(farewell_router)
api_router.include_router(cremation_router)
api_router.include_router(product_router)
api_router.include_router(billing_router)
api_router.include_router(dashboard_router)
