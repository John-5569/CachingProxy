import argparse
import cachingProxy
import uvicorn

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--port", type=int, required=False)
    parser.add_argument("--origin", type=str, required=False)
    parser.add_argument("--clear-cache", action="store_true")

    args = parser.parse_args()

    if args.clear_cache:
        cachingProxy.r.flushdb()
        print("✅ Cleared the cache.")
        return
    
    if not args.port or not args.origin:
        print("❌ Please provide both --port and --origin")
        print("Example: python3 main.py --port 3000 --origin http://dummyjson.com")
        return
    
    # Remove trailing slash if present
    cachingProxy.ORIGIN = args.origin.rstrip("/")

    print(f"🚀 Starting caching proxy server...")
    print(f"📍 Origin: {cachingProxy.ORIGIN}")
    print(f"🔌 Port: {args.port}")
    print(f"💾 Cache TTL: {cachingProxy.TTL} seconds")
    print(f"📡 Server running at: http://localhost:{args.port}")
    
    uvicorn.run(cachingProxy.app, host="0.0.0.0", port=args.port)

if __name__ == "__main__":
    main()