import asyncio
import logging
from cbpi.api import *
import aiohttp

logger = logging.getLogger("cbpi4-HA-Actor")


@parameters([
    Property.Select(
        label="Check Certificate",
        options=["YES", "NO"],
        description="Enable or disable TLS certificate checking"
    ),
    Property.Number(
        label="Request Timeout",
        configurable=True,
        description="HTTP timeout in seconds",
        default_value=5
    ),
    Property.Text(
        label="Base API entry point",
        configurable=True,
        description="Home Assistant API base URL (e.g. http://home:8123/api)"
    ),
    Property.Text(
        label="Entity id",
        configurable=True,
        description="Home Assistant entity id (e.g. switch.pump)"
    ),
    Property.Text(
        label="Authorization Token",
        configurable=True,
        description="HA Long-Lived Access Token"
    ),
    Property.Number(
        label="EasyPWM sampling time",
        configurable=True,
        description="PWM base interval in seconds",
        default_value=5
    ),
    Property.Number(
        label="Status Poll Interval",
        configurable=True,
        description="Interval (seconds) to poll HA state",
        default_value=5
    )
])
class HAActor(CBPiActor):

    def __init__(self, cbpi, id, props):
        """Guaranteed to run before any other lifecycle method — use for safe defaults."""
        super().__init__(cbpi, id, props)

        # config placeholders (will be filled in on_start)
        self.entity = None
        self.domain = None
        self.object = None

        self.base_url = None
        self.headers = {}
        self.verify_ssl = True

        self.timeout = 5
        self.sample_time = 5
        self.poll_interval = 5

        # runtime state defaults
        self.power = 0
        self.state = False

        # aiohttp session placeholder
        self.session = None

        # background task handle
        self._poll_task = None

        logger.debug("[HAActor] __init__ completed (defaults set)")

    async def on_start(self):
        """Called when plugin is started/initialized by CBPi."""
        try:
            self.entity = (self.props.get("Entity id") or "").strip()
            if not self.entity or "." not in self.entity:
                logger.error("[HAActor] Invalid or missing Entity id in plugin properties")
                return

            self.domain, self.object = self.entity.split(".", 1)

            self.base_url = (self.props.get("Base API entry point") or "").rstrip("/")
            if not self.base_url:
                logger.error("[HAActor] Missing Base API entry point")
                return

            self.timeout = int(self.props.get("Request Timeout") or 5)
            self.sample_time = int(self.props.get("EasyPWM sampling time") or 5)
            self.poll_interval = int(self.props.get("Status Poll Interval") or 5)
            self.verify_ssl = (self.props.get("Check Certificate") == "YES")

            token = (self.props.get("Authorization Token") or "").strip()
            self.headers = {"Content-Type": "application/json"}
            if token:
                self.headers["Authorization"] = f"Bearer {token}"

            # create aiohttp session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )

            logger.info(f"[HAActor] on_start: entity={self.entity}, base_url={self.base_url}")
            logger.info(f"[HAActor] Poll interval={self.poll_interval}s, sample_time={self.sample_time}s")

            # start polling task (store handle so we can cancel it later)
            self._poll_task = asyncio.create_task(self.poll_state())

        except Exception as e:
            logger.exception(f"[HAActor] Exception in on_start: {e}")

    async def poll_state(self):
        """Poll Home Assistant for the entity state periodically and sync local state."""
        # small initial delay so system has time to set running flag etc.
        await asyncio.sleep(1)

        logger.debug("[HAActor] poll_state started")

        while True:
            # Only poll when the actor is marked running by CBPi; otherwise wait and retry.
            if not getattr(self, "running", False):
                await asyncio.sleep(0.5)
                continue

            # If session isn't ready, wait until it is (should be created in on_start)
            if self.session is None:
                logger.debug("[HAActor] poll_state: session not ready yet, waiting")
                await asyncio.sleep(0.5)
                continue

            try:
                url = f"{self.base_url}/states/{self.entity}"
                async with self.session.get(url, headers=self.headers, ssl=self.verify_ssl) as resp:
                    text = await resp.text()
                    if resp.status == 200:
                        try:
                            data = await resp.json()
                        except Exception:
                            logger.warning(f"[HAActor] poll_state: invalid JSON from HA: {text}")
                            data = None

                        if data:
                            ha_state = data.get("state")
                            attributes = data.get("attributes", {})

                            new_state = (ha_state == "on")

                            if new_state != self.state:
                                logger.info(f"[HAActor] HA state mismatch -> updating local state to {new_state}")
                                self.state = new_state
                                # Let CBPi UI know (update actor power/status)
                                try:
                                    await self.cbpi.actor.actor_update(self.id, self.power)
                                except Exception as e:
                                    logger.debug(f"[HAActor] actor_update failed: {e}")

                            # Sync percentage if present
                            if "percentage" in attributes:
                                try:
                                    new_power = int(round(float(attributes.get("percentage", self.power))))
                                except Exception:
                                    new_power = self.power
                                if new_power != self.power:
                                    logger.info(f"[HAActor] HA percentage changed -> updating local power to {new_power}")
                                    self.power = new_power
                                    try:
                                        await self.cbpi.actor.actor_update(self.id, self.power)
                                    except Exception:
                                        pass
                    else:
                        logger.warning(f"[HAActor] poll_state: HTTP {resp.status} from {url} - body: {text}")

            except asyncio.CancelledError:
                logger.debug("[HAActor] poll_state cancelled")
                break
            except Exception as e:
                logger.exception(f"[HAActor] Exception in poll_state: {e}")

            await asyncio.sleep(self.poll_interval)

    async def send_service(self, service):
        """Call HA service (turn_on / turn_off). Safe if session isn't ready yet."""
        if self.session is None:
            logger.warning("[HAActor] send_service called but session not ready; skipping service call")
            return

        url = f"{self.base_url}/services/{self.domain}/{service}"
        payload = {"entity_id": self.entity}

        try:
            async with self.session.post(url, json=payload, headers=self.headers, ssl=self.verify_ssl) as resp:
                text = await resp.text()
                if resp.status not in (200, 201):
                    logger.warning(f"[HAActor] Service {service} failed: HTTP {resp.status} - {text}")
                else:
                    logger.debug(f"[HAActor] Service {service} OK")
        except Exception as e:
            logger.exception(f"[HAActor] Service call error ({service}): {e}")

    async def on(self, power=None):
        """Requested to turn actor ON (via CBPi UI / script)."""
        if power is not None:
            try:
                self.power = int(power)
            except Exception:
                self.power = self.power

        self.state = True
        await self.send_service("turn_on")
        # ensure cbpi sees latest power
        try:
            await self.cbpi.actor.actor_update(self.id, self.power)
        except Exception:
            pass

    async def off(self):
        """Requested to turn actor OFF (via CBPi UI / script)."""
        self.state = False
        await self.send_service("turn_off")
        try:
            await self.cbpi.actor.actor_update(self.id, self.power)
        except Exception:
            pass

    async def run(self):
        """PWM loop (runs continually). Safe even if on_start hasn't run yet."""
        logger.debug("[HAActor] run loop started")
        while True:
            # wait until CBPi actually marked this actor running
            if not getattr(self, "running", False):
                await asyncio.sleep(0.5)
                continue

            # if state is on, perform PWM cycle based on self.power and sample_time
            if self.state:
                heat = self.sample_time * (self.power / 100.0)
                cool = max(0.0, self.sample_time - heat)

                if heat > 0:
                    logger.debug(f"[HAActor] PWM: ON for {heat:.2f}s (power={self.power})")
                    await self.send_service("turn_on")
                    # don't block forever if canceled externally
                    try:
                        await asyncio.sleep(heat)
                    except asyncio.CancelledError:
                        break

                if cool > 0:
                    logger.debug(f"[HAActor] PWM: OFF for {cool:.2f}s")
                    await self.send_service("turn_off")
                    try:
                        await asyncio.sleep(cool)
                    except asyncio.CancelledError:
                        break
            else:
                # actor is off — sleep briefly and loop
                await asyncio.sleep(0.5)

    async def set_power(self, power):
        """Set power from CBPi UI (0-100)."""
        try:
            self.power = int(round(float(power)))
        except Exception:
            logger.warning(f"[HAActor] set_power: invalid power value {power}")
            return

        logger.info(f"[HAActor] set_power -> {self.power}")
        if self.state:
            await self.on(self.power)

        try:
            await self.cbpi.actor.actor_update(self.id, self.power)
        except Exception:
            pass

    def get_state(self):
        """Return boolean state for CBPi UI."""
        return bool(self.state)

    async def on_shutdown(self):
        """Cleanup: cancel poll task and close aiohttp session"""
        logger.info("[HAActor] on_shutdown called — cleaning up")
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"[HAActor] poll_task cancellation error: {e}")

        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                logger.debug(f"[HAActor] session close error: {e}")

        logger.info("[HAActor] cleanup done")


def setup(cbpi):
    cbpi.plugin.register("HomeAssistant Actor", HAActor)
