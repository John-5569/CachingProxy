import httpx
import redis
from fastapi import FastAPI ,Request,Response
import json
import os
from dotenv import load_dotenv

app=FastAPI()

REDIS_URL =os.getenv("REDIS_URL")
r=redis.Redis.from_url(REDIS_URL,decode_response=False)
ORIGIN=None
TTL=60


def getCacheKey(request:Request):
    return f"{request.method}:{request.url.path}?{request.url.query}"

@app.apiRoute("/{path:path}",methods=["GET","POST","PUT","DELETE"])
async def proxy(request:Request ,path:str):

    cacheKey=getCacheKey(request)

    if request.method=="GET":
        cached=r.get(cacheKey)

        if cached:
            data=json.loads(cached)

            return Response(
                content=bytes.fromhex(data["content"]),
                status_code=data["status"],
                headers={**data["headers"] ,"X-Cache":"HIT"}

            )

    async with httpx.AsyncClient() as client:
        url=f"{ORIGIN}/{path}"
        if request.url.query:
            url+=f"?{request.url.query}"

        body=await request.body()
        
        origin_response=await client.request(
            method=request.method,
            url=url,
            headers=request.headers.raw,
            content=body
        )

    response_content=origin_response.content

    if request.method=="GET" and origin_response.status_code==200:
        data={
            "content":response_content.hex(),
            "status":origin_response.status_code,
            "headers":dict(origin_response.headers)
        }
        r.setex(cacheKey,TTL,json.dumps(data))
    
    return Response(
        content=response_content,
        status_code=origin_response.status_code,
        headers={**origin_response.headers,"X-Cache":"MISS"}
    )


@app.get("/--clear_cache")
def clear_cache():
    r.flushdb()
    return {"message":"Cache cleared"}