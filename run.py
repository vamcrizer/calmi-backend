"""
Calmi Server - Quick start script.
Usage: python run.py
"""
import os
import uvicorn

if __name__ == "__main__":
    # Check if running in production
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=not is_production,  # Disable reload in production
        log_level="info",
        workers=4 if is_production else 1,  # Multiple workers in production
    )
