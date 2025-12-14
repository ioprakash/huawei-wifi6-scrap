import asyncio
import random
import ssl
import sys

TARGETS = [
    ("google.com", 443),
    ("cloudflare.com", 443),
    ("amazon.com", 443),
    ("facebook.com", 443),
]

CONNECTIONS = 15000        # AsyncIO allows high concurrency
DOWNLOAD_BYTES = 1024*100  # per connection
RUN_TIME = 600            # seconds

async def worker(context, stop_event):
    while not stop_event.is_set():
        writer = None
        try:
            host, port = random.choice(TARGETS)
            
            # Async connection with SSL
            # Note: limit connection setup rate if necessary, but for stress test we go full speed
            reader, writer = await asyncio.open_connection(host, port, ssl=context)
            
            req = f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
            writer.write(req.encode())
            await writer.drain()

            received = 0
            while received < DOWNLOAD_BYTES and not stop_event.is_set():
                data = await reader.read(4096)
                if not data:
                    break
                received += len(data)
                
        except Exception:
            # Expected errors: connection refused, timeout, reset, etc.
            # Sleep briefly to avoid busy-looping if network is down or limits hit
            await asyncio.sleep(1)
            
        finally:
            if writer:
                try:
                    writer.close()
                    # We should wait for it to close, but avoid hanging indefinitely
                    await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
                except Exception:
                    pass

async def main():
    print(f"Starting AsyncIO stress test with {CONNECTIONS} concurrent tasks...")
    
    # Shared SSL context (optimization: create once)
    context = ssl.create_default_context()
    
    stop_event = asyncio.Event()
    tasks = []

    # Launch workers
    # staggering start slightly can help avoid initial spike issues, but not required
    for _ in range(CONNECTIONS):
        tasks.append(asyncio.create_task(worker(context, stop_event)))
        
    # Run loop
    try:
        await asyncio.sleep(RUN_TIME)
    except asyncio.CancelledError:
        pass
        
    print("Time's up. Stopping workers...")
    stop_event.set()
    
    # Cancel all tasks
    for t in tasks:
        t.cancel()
        
    # Wait for clean shutdown
    await asyncio.gather(*tasks, return_exceptions=True)
    print("Test finished.")

if __name__ == "__main__":
    # Windows loop policy check if needed (Python 3.8+ defaults to Proactor which is good)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
