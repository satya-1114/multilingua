from fastapi import APIRouter

router = APIRouter(prefix="/communication", tags=["Communication"])


@router.post("/send")
def send_campaign():
    pass


@router.get("/deliveries")
def list_deliveries():
    pass


@router.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: str):
    pass


@router.get("/deliveries/{delivery_id}/logs")
def get_delivery_logs(delivery_id: str):
    pass


@router.get("/providers")
def provider_health():
    pass