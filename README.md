# LoadLoad

A high-performance, asynchronous HTTP load balancer built with Python and aiohttp, featuring health checks, sticky sessions, and automatic failover.

## Features

- **Round-Robin Load Balancing** - Distributes requests evenly across healthy backend servers
- **Health Monitoring** - Continuous health checks with automatic server recovery
- **Sticky Sessions** - Session persistence using cookies, headers, or IP-based routing
- **Async/Await Architecture** - Built on aiohttp for high concurrency and performance
- **Auto Failover** - Automatically removes unhealthy servers from rotation
- **Monitoring Endpoints** - Built-in health and statistics endpoints
- **Test Backends Included** - Mock backend servers for development and testing

## Installation

```bash
pip install aiohttp
```

## Quick Start

```bash
# Clone the repository
git clone <your-repo-url>
cd loadload

# Run the load balancer with test backends
python load_balancer.py
```

The load balancer will start on `http://localhost:8000` with test backends running on ports 8001-8003.

## Usage

### Basic Requests
```bash
# Make requests through the load balancer
curl http://localhost:8000/
curl http://localhost:8000/api/data
```

### Sticky Sessions
```bash
# Using session cookie
curl -
