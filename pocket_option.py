import json
import asyncio
import websockets
import time

class PocketOptionClient:
    def __init__(self, ssid):
        self.ssid = ssid
        self.ws_url = "wss://api-us-north.po.market/socket.io/?EIO=4&transport=websocket"
        self.ws = None

    async def connect(self):
        """Establishes connection and authenticates using the SSID."""
        try:
            self.ws = await websockets.connect(self.ws_url)
            # Send the authentication string from your .env
            await self.ws.send(self.ssid)
            
            # Pocket Option requires a heartbeat/ping to stay alive
            asyncio.create_task(self.heartbeat())
            print("[✅] Pocket Option: Connected and Authenticated.")
            return True
        except Exception as e:
            print(f"[❌] Pocket Option Connection Error: {e}")
            return False

    async def heartbeat(self):
        """Sends '3' (the standard Engine.io ping) every 25 seconds."""
        while self.ws and self.ws.open:
            await self.ws.send("3")
            await asyncio.sleep(25)

    async def place_order(self, asset, amount, direction, duration):
        """
        Executes a trade.
        direction: 'call' (UP) or 'put' (DOWN)
        duration: time in seconds (e.g., 300 for 5 mins)
        """
        if not self.ws or not self.ws.open:
            connected = await self.connect()
            if not connected:
                return "FAILED: Could not connect to Pocket Option"

        # Simplified PO trade packet structure
        trade_msg = {
            "action": "openOrder",
            "data": {
                "asset": asset,
                "amount": amount,
                "direction": direction.lower(),
                "time": duration
            }
        }
        
        # Binary protocol usually requires a prefix (e.g., '42') for Socket.io
        await self.ws.send(f'42{json.dumps(trade_msg)}')
        print(f"[🚀] Order Sent: {direction.upper()} {asset} for ${amount}")
        return "SUCCESS"

    async def close(self):
        if self.ws:
            await self.ws.close()