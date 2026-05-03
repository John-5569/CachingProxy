import argparse
import cachingProxy

def main():
    parser=argparse.ArugmentParser()

    parser.add_arugment("--port",type=int)
    parser.add_arugment("--origin",type=str)
    parser.add_arugment("--clear-cache",action="store_true")

    args=parser.parse_args()

    if args.clear_cache:
        cachingProxy.r.flushdb()
        print(" ✅ Cleared the cache .")
        return 
    
    if not args.port or not args.origin:
        print(" ❌ Provide --port and --origin .")
    
    cachingProxy.ORIGIN=args.origin.rstrip("/")

if __name__=="__main__":
    main()

