import sys
import asyncio
import logging
import random
from unittest.mock import MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
_LOG = logging.getLogger("reproduce")

class MockJvcProjector:
    def __init__(self, host, password):
        self.host = host
        self.password = password
        self.active_calls = 0

    async def connect(self):
        await self._simulate_call("connect", 0.5)

    async def get_state(self):
        await self._simulate_call("get_state", 0.2)
        return {"power": "on", "input": "hdmi1", "source": "no_signal"}

    async def ref(self, command):
        await self._simulate_call(f"ref({command})", 0.3)
        return "some_value"

    async def power_on(self):
        await self._simulate_call("power_on", 0.5)

    async def power_off(self):
        await self._simulate_call("power_off", 0.5)

    async def remote(self, code):
        await self._simulate_call(f"remote({code})", 0.1)

    async def op(self, code):
        await self._simulate_call(f"op({code})", 0.1)

    async def get_power(self):
        await self._simulate_call("get_power", 0.1)
        return "on"

    async def _simulate_call(self, name, duration):
        # Check for concurrency
        if self.active_calls > 0:
            _LOG.error(f"CONCURRENCY DETECTED! Call {name} started while {self.active_calls} other calls active.")

        self.active_calls += 1
        try:
            _LOG.info(f"Start {name}")
            await asyncio.sleep(duration)
            _LOG.info(f"End {name}")
        finally:
            self.active_calls -= 1

# Mock modules before importing projector
sys.modules["jvcprojector"] = MagicMock()
sys.modules["jvcprojector.const"] = MagicMock()
sys.modules["jvcprojector.projector"] = MagicMock()
sys.modules["jvcprojector.projector"].JvcProjector = MockJvcProjector

sys.path.append("intg-jvc")
from projector import JVCProjector
from const import JVCConfig

async def main():
    # Setup
    config = MagicMock(spec=JVCConfig)
    config.identifier = "test_jvc"
    config.name = "Test JVC"
    config.address = "1.2.3.4"
    config.password = "pass"

    # We need to mock aiohttp too maybe?
    # JVCProjector inherits StatelessHTTPDevice which probably uses it.
    # But we mock JvcProjector calls so it shouldn't matter unless init does something.

    device = JVCProjector(config, asyncio.get_event_loop())

    async def poller():
        for i in range(3):
            _LOG.info(f"Poll {i}")
            # verify_connection spawns a task, so we need to wait a bit to let it run
            await device.verify_connection()
            await asyncio.sleep(1.5)

    async def user_action():
        await asyncio.sleep(1.0)
        _LOG.info("User action: Cursor Down")
        await device.send_command("remote", code="down")

    await asyncio.gather(poller(), user_action())

if __name__ == "__main__":
    asyncio.run(main())
