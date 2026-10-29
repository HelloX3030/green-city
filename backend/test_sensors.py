import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import history
import sensors

CACHE = {
    "boxes": {"box1": {"name": "Kiliansplatz", "lat": 49.14, "lon": 9.22, "phenomena": {
        "temp": {"title": "Temperatur", "fine": {"2026-10-28T22:45Z": 9.5, "2026-10-28T23:00Z": 9.1}},
        "noise": {"title": "LAeq_1min", "fine": {"2026-10-28T23:00Z": None, "2026-10-28T22:45Z": 52.3}},
    }}},
    "uba": {"pm25": {"fine": {"2026-10-28T23:00Z": 7}}},
}


class Down:
    """An httpx client whose every request fails, like openSenseMap and UBA at their worst."""
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def get(self, *_, **__):
        raise OSError("down")


class Fallbacks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        history.CACHE_PATH = Path(self.tmp.name) / "none.json"
        history._cache = CACHE
        sensors._state.update({"boxes": [], "boxes_at": 0.0, "sensors": [], "at": 0.0})

    def tearDown(self):
        self.tmp.cleanup()

    def refresh(self):
        with mock.patch.object(sensors.httpx, "AsyncClient", Down):
            asyncio.run(sensors._refresh())
        return {s["id"]: s for s in sensors._state["sensors"]}

    def test_all_down_on_start_pins_and_last_hour_from_history(self):
        got = self.refresh()
        box, uba = got["box1"], got["DEBW015"]
        self.assertEqual((box["name"], box["lat"], box["lon"], box["kind"]), ("Kiliansplatz", 49.14, 9.22, "noise"))
        self.assertEqual([(v["key"], v["value"], v["label"]) for v in box["values"]],
                         [("temp", 9.1, "Temperatur"), ("noise", 52.3, "Lärm Ø 15 min")])
        self.assertEqual(box["last"], "2026-10-28T23:00:00+00:00")
        self.assertEqual([(v["key"], v["value"], v["unit"]) for v in uba["values"]], [("pm25", 7.0, "µg/m³")])

    def test_down_later_keeps_the_last_live_values(self):
        live = [{"key": "temp", "label": "Temperatur", "value": 11.0, "unit": "°C", "time": "2026-10-29T01:00:00Z"}]
        sensors._state["sensors"] = [{"id": "box1", "values": live}]
        self.assertEqual(self.refresh()["box1"]["values"], live)

    def test_stale_answer_comes_at_once_and_refreshes_behind(self):
        old = [{"id": "box1", "values": []}]
        sensors._state.update({"sensors": old, "at": 1.0})

        async def run():
            with mock.patch.object(sensors, "_refresh", mock.AsyncMock()) as r:
                self.assertIs(await sensors.get_sensors(), old)
                await sensors._task
                r.assert_awaited_once()
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
