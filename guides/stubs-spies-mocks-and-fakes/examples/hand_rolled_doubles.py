"""A dummy, a stub, a spy and a fake, written by hand, in the tests of a thermostat.

The thermostat reads a temperature from a sensor, reads its target from a settings store and
switches a heater. It calls the alarm only when the room is dangerously cold. In a test, the real
sensor, store and heater are replaced by doubles that the test controls and inspects.
"""


class Thermostat:
    def __init__(self, sensor, heater, settings, alarm):
        self.sensor, self.heater, self.settings, self.alarm = sensor, heater, settings, alarm

    def tick(self) -> None:
        target = self.settings.get("target")
        reading = self.sensor.read()
        if reading < 5:
            self.alarm.ring(f"room at {reading} degrees")
        if reading < target - 0.5:
            self.heater.switch(True)
        elif reading > target + 0.5:
            self.heater.switch(False)


class StubSensor:
    """Gives the readings the test scripted, one per call."""

    def __init__(self, *readings: float):
        self.readings = list(readings)

    def read(self) -> float:
        return self.readings.pop(0)


class SpyHeater:
    """Does nothing, but records every call for the test to inspect afterwards."""

    def __init__(self):
        self.calls: list[bool] = []

    def switch(self, on: bool) -> None:
        self.calls.append(on)


class FakeSettings:
    """A working store, kept in a dictionary instead of a file on disk."""

    def __init__(self, **values):
        self.values = dict(values)

    def get(self, key):
        return self.values[key]

    def set(self, key, value) -> None:
        self.values[key] = value


DUMMY_ALARM = None  # never used on these paths; a call to it would fail loudly


def test_cold_room_turns_the_heater_on():
    heater = SpyHeater()
    Thermostat(StubSensor(17.0), heater, FakeSettings(target=20), DUMMY_ALARM).tick()
    assert heater.calls == [True], heater.calls


def test_room_in_range_leaves_the_heater_alone():
    heater = SpyHeater()
    Thermostat(StubSensor(20.3), heater, FakeSettings(target=20), DUMMY_ALARM).tick()
    assert heater.calls == [], heater.calls


def test_a_lower_target_turns_the_heater_off():
    heater, settings = SpyHeater(), FakeSettings(target=21)
    thermostat = Thermostat(StubSensor(19.0, 19.0), heater, settings, DUMMY_ALARM)
    thermostat.tick()
    settings.set("target", 18)
    thermostat.tick()
    assert heater.calls == [True, False], heater.calls


for test in (test_cold_room_turns_the_heater_on, test_room_in_range_leaves_the_heater_alone,
             test_a_lower_target_turns_the_heater_off):
    test()
    print(f"passed: {test.__name__}")

try:
    Thermostat(StubSensor(3.0), SpyHeater(), FakeSettings(target=20), DUMMY_ALARM).tick()
except AttributeError as error:
    print(f"a freezing room reaches the dummy: {error}")
