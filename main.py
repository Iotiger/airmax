from fastapi import FastAPI
from app.integrations import router as integrations_router

app = FastAPI(
    title="FareHarbor Webhook API", 
    version="1.0.0",
    description="Modular webhook API for FareHarbor integrations"
)

# Include integrations router as the main endpoint
app.include_router(
    integrations_router, 
    prefix="/integrations/fareharbor/webhooks",
    tags=["integrations"]
)

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Check if SSL certificates exist
    if os.path.exists("key.pem") and os.path.exists("cert.pem"):
        print("[HTTPS] Starting server with HTTPS...")
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=8000, 
            reload=True,
            ssl_keyfile="key.pem",
            ssl_certfile="cert.pem"
        )
    else:
        print("[HTTP] SSL certificates not found. Running on HTTP only.")
        print("Run 'python generate_ssl.py' to generate certificates for HTTPS")
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
