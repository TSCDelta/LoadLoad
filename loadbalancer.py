import asyncio
import aiohttp
import time
import logging
from aiohttp import web, ClientSession
from typing import List, Dict, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Server:
    host: str
    port: int
    is_healthy: bool = True
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

class LoadLoad:
    def __init__(self, servers: List[Server]):
        self.servers = servers
        self.current_index = 0
        self.sticky_sessions: Dict[str, Server] = {}
        self.session = None
        
    async def start(self):
        self.session = ClientSession()
        asyncio.create_task(self._health_check_loop())
        
    async def stop(self):
        if self.session:
            await self.session.close()
    
    def _get_session_id(self, request: web.Request) -> Optional[str]:
        session_id = request.cookies.get('session_id')
        if session_id:
            return session_id
        return request.remote
    
    def _round_robin(self) -> Optional[Server]:
        healthy_servers = [s for s in self.servers if s.is_healthy]
        if not healthy_servers:
            return None
            
        server = healthy_servers[self.current_index % len(healthy_servers)]
        self.current_index += 1
        return server
    
    def _get_server(self, session_id: str) -> Optional[Server]:
        if session_id in self.sticky_sessions:
            server = self.sticky_sessions[session_id]
            if server.is_healthy:
                return server
            else:
                del self.sticky_sessions[session_id]
        
        server = self._round_robin()
        if server:
            self.sticky_sessions[session_id] = server
            logger.info(f"Assigned session {session_id} to {server.url}")
        
        return server
    
    async def _check_health(self, server: Server):
        try:
            async with self.session.get(f"{server.url}/health", timeout=5) as response:
                server.is_healthy = (response.status == 200)
        except Exception:
            server.is_healthy = False
            
    async def _health_check_loop(self):
        while True:
            for server in self.servers:
                await self._check_health(server)
            await asyncio.sleep(10)
    
    async def handle_request(self, request: web.Request) -> web.Response:
        session_id = self._get_session_id(request)
        
        if session_id:
            server = self._get_server(session_id)
        else:
            server = self._round_robin()
            
        if not server:
            return web.Response(text="No servers available", status=503)
        
        try:
            async with self.session.request(
                method=request.method,
                url=f"{server.url}{request.path_qs}",
                headers={k: v for k, v in request.headers.items() if k.lower() != 'host'},
                data=await request.read() if request.body_exists else None
            ) as response:
                body = await response.read()
                return web.Response(
                    body=body,
                    status=response.status,
                    headers=dict(response.headers)
                )
        except Exception as e:
            logger.error(f"Error proxying to {server.url}: {e}")
            return web.Response(text="Backend error", status=502)

async def create_app(servers: List[Server]) -> web.Application:
    app = web.Application()
    lb = LoadLoad(servers)
    
    async def startup(app):
        await lb.start()
    
    async def cleanup(app):
        await lb.stop()
    
    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)
    
    app.router.add_route('*', '/{path:.*}', lb.handle_request)
    return app

SERVERS = [
    Server("localhost", 8001),
    Server("localhost", 8002),
    Server("localhost", 8003),
]

async def create_backend(port: int):
    async def handler(request):
        return web.json_response({
            'server': f'localhost:{port}',
            'path': request.path
        })
    
    async def health(request):
        return web.json_response({'status': 'ok'})
    
    app = web.Application()
    app.router.add_get('/', handler)
    app.router.add_get('/health', health)
    return app

async def main():
    backends = []
    for server in SERVERS:
        app = await create_backend(server.port)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, server.host, server.port)
        await site.start()
        backends.append(runner)
    
    lb_app = await create_app(SERVERS)
    lb_runner = web.AppRunner(lb_app)
    await lb_runner.setup()
    lb_site = web.TCPSite(lb_runner, 'localhost', 8000)
    await lb_site.start()
    
    logger.info("LoadLoad started on http://localhost:8000")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        for runner in backends + [lb_runner]:
            await runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())