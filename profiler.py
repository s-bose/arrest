from arrest import Resource, Service
from arrest.exceptions import ArrestHTTPException
from fastapi.exceptions import HTTPException
import asyncio
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

json = Resource(route="/json", handlers=[("GET", "")])
status = Resource(route="/status", handlers=[("GET", "/404"), ("GET", "/500"), ("GET", "/418")])
delay = Resource(route="/delay", handlers=[("GET", "/{delay_sec}")])

svc = Service(name="svc", url="http://httpbin.org", resources=[json, status, delay])

delay_sec = 10
# resp = await svc.delay.get(f"/{delay_sec}")


async def runner():
    resp = await svc.status.get("/500")
    print(resp)


if __name__ == "__main__":
    asyncio.run(runner())
