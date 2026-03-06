from __future__ import annotations
from fastmcp import FastMCP
import requests
from dotenv import load_dotenv
import os
load_dotenv()

mcp = FastMCP('arith & stocks')

def _as_number(x):
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        return float(x.strip())
    raise TypeError("Expected a number (int/float or numeric string)")

@mcp.tool()
async def add(a: float, b: float):
    """Return a + b."""
    return _as_number(a) + _as_number(b)

@mcp.tool()
async def subtract(a: float, b: float):
    """Return a - b."""
    return _as_number(a) - _as_number(b)

@mcp.tool()
async def multiply(a: float, b: float):
    """Return a * b."""
    return _as_number(a) * _as_number(b)

@mcp.tool()
async def divide(a: float, b: float):
    """Return a / b.  Raises on division by zero."""
    a = _as_number(a)
    b = _as_number(b)
    if b == 0:
        raise ZeroDivisionError("Division by Zero!")
    return a / b

@mcp.tool()
async def power(a: float, b: float):
    """Return a ** b."""
    return _as_number(a) ** _as_number(b)

@mcp.tool()
async def modulus(a: float, b: float):
    """Return a % b. Raises on modulus by zero."""
    a = _as_number(a)
    b = _as_number(b)
    if b == 0:
        raise ZeroDivisionError("Modulus by Zero!")
    return _as_number(a) % _as_number(b)

@mcp.tool()
async def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    api_key = os.getenv('ALPHAVANTAGE')
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
    r = requests.get(url)
    return r.json()

if __name__ == "__main__":
    # mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
    mcp.run()