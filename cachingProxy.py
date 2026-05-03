import httpx
import redis
from fastapi import FastAPI, Request, Response
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
r = redis.Redis.from_url(REDIS_URL, decode_responses=False)
ORIGIN = None
TTL = 60

def getCacheKey(request: Request):
    return f"{request.method}:{request.url.path}?{request.url.query}"

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    
    cacheKey = getCacheKey(request)

    # Check cache for GET requests
    if request.method == "GET":
        cached = r.get(cacheKey)
        if cached:
            data = json.loads(cached)
            content = bytes.fromhex(data["content"])
            headers = data["headers"]
            headers["X-Cache"] = "HIT"
            
            return Response(
                content=content,
                status_code=data["status"],
                headers=headers
            )

    # Forward request to origin
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Construct the full URL
        if path:
            url = f"{ORIGIN}/{path}"
        else:
            url = ORIGIN
        
        # Add query parameters if they exist
        if request.url.query:
            url += f"?{request.url.query}"
        
        # Get request body
        body = await request.body()
        
        # Prepare headers - remove host header that points to proxy
        headers = dict(request.headers)
        headers.pop("host", None)
        
        try:
            # Make request to origin server with follow_redirects=True
            origin_response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body if body else None,
                follow_redirects=True  # This will automatically follow redirects
            )
        except httpx.ConnectError:
            return Response(
                content=json.dumps({"error": f"Cannot connect to origin server: {ORIGIN}"}),
                status_code=502,
                media_type="application/json"
            )
        except Exception as e:
            return Response(
                content=json.dumps({"error": str(e)}),
                status_code=500,
                media_type="application/json"
            )

    response_content = origin_response.content
    response_headers = dict(origin_response.headers)
    response_headers["X-Cache"] = "MISS"

    # Cache successful GET responses (200 OK only, not redirects)
    if request.method == "GET" and origin_response.status_code == 200:
        data = {
            "content": response_content.hex(),
            "status": origin_response.status_code,
            "headers": response_headers
        }
        r.setex(cacheKey, TTL, json.dumps(data))
        print(f"✅ Cached: {cacheKey} (Status: {origin_response.status_code})")
    else:
        print(f"⏭️ Not caching: {cacheKey} (Method: {request.method}, Status: {origin_response.status_code})")

    return Response(
        content=response_content,
        status_code=origin_response.status_code,
        headers=response_headers
    )

@app.get("/--clear_cache")
def clear_cache():
    r.flushdb()
    return {"message": "Cache cleared"}

@app.get("/cache/stats")
def cache_stats():
    return {
        "cache_enabled": True,
        "ttl_seconds": TTL,
        "origin": ORIGIN,
        "redis_connected": r.ping()
    }