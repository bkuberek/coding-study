"""The same kinds of double with unittest.mock, its safety nets, and where to patch.

A Mock answers every call and records it, so it serves as a stub and a spy at once. A spec
limits it to the real object's attributes, autospeccing also checks the arguments, and patch()
replaces a name only in the module whose lookup it changes.
"""

import sys
import types
from unittest.mock import Mock, call, create_autospec, patch


class Heater:
    def switch(self, on: bool) -> None:
        raise RuntimeError("the real heater is not connected in tests")


def control(sensor, heater, target: float) -> None:
    reading = sensor.read()
    if reading < target - 0.5:
        heater.switch(True)
    elif reading > target + 0.5:
        heater.switch(False)


# A stub and a spy in one: side_effect scripts the answers, call_args_list records the calls.
sensor = Mock()
sensor.read.side_effect = [17.0, 22.0]
heater = Mock(spec=Heater)
control(sensor, heater, 20)
control(sensor, heater, 20)
print("calls recorded:", heater.switch.call_args_list == [call(True), call(False)])
heater.switch.assert_called_with(False)
print("last call was switch(False)")

# Without a spec, a renamed or misspelled method still "works", and a test can pass for nothing.
print("unspecced mock accepts turn_on():", Mock().turn_on() is not None)
try:
    heater.turn_on()
except AttributeError as error:
    print("spec refuses it:", type(error).__name__)

# Names that look like a misspelled assertion are refused too.
try:
    heater.switch.assret_called_once()
except AttributeError as error:
    print("typo caught:", type(error).__name__)

# Autospeccing also checks the arguments against the real signature.
strict_heater = create_autospec(Heater, instance=True)
try:
    strict_heater.switch(True, "fast")
except TypeError as error:
    print("autospec refuses the call:", type(error).__name__)

# Where to patch: in the module that looks the name up, not the one that defines it.
weather = types.ModuleType("weather")
exec("def read_celsius():\n    raise RuntimeError('no network in tests')\n", weather.__dict__)
sys.modules["weather"] = weather
dashboard = types.ModuleType("dashboard")
exec("from weather import read_celsius\n\n"
     "def headline():\n    return f'{read_celsius():.0f} degrees'\n", dashboard.__dict__)
sys.modules["dashboard"] = dashboard

with patch("weather.read_celsius", return_value=21.4):
    try:
        dashboard.headline()
    except RuntimeError as error:
        print("patched weather.read_celsius, but dashboard still calls the real one:", error)
with patch("dashboard.read_celsius", return_value=21.4):
    print("patched dashboard.read_celsius:", dashboard.headline())
