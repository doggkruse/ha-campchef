"""Run with Home Assistant and pycampchef installed; no BLE hardware required."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from homeassistant.components.climate import ClimateEntityFeature, HVACMode
from homeassistant.exceptions import HomeAssistantError
from pycampchef.const import ModeName
from pycampchef.models import GrillChamber, GrillMode, GrillState

from custom_components.camp_chef.climate import CampChefThermostat


class ShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.commands = SimpleNamespace(shutdown=AsyncMock(), read_mode=AsyncMock())
        self.original = GrillState(
            mode=GrillMode(mode=ModeName.RUN, set_temp_f=275, smoke_level=1),
            chamber=GrillChamber(i16=260, temp_f=260),
        )
        self.coordinator = SimpleNamespace(
            config_entry=None,
            data=self.original,
            client=SimpleNamespace(commands=self.commands),
            async_set_updated_data=Mock(),
        )
        entry = SimpleNamespace(data={"address": "00:11:22:33:44:55"})
        self.entity = CampChefThermostat(self.coordinator, entry, "Test grill")

    async def test_turn_off_publishes_readback_without_mutating_old_state(self):
        observed = GrillMode(mode=ModeName.STANDBY)
        self.commands.read_mode.return_value = observed
        await self.entity.async_turn_off()
        self.commands.shutdown.assert_awaited_once()
        self.commands.read_mode.assert_awaited_once()
        updated = self.coordinator.async_set_updated_data.call_args.args[0]
        self.assertIs(updated.mode, observed)
        self.assertIs(updated.chamber, self.original.chamber)
        self.assertIsNot(updated, self.original)
        self.assertEqual(self.original.mode.mode, ModeName.RUN)

    async def test_write_failure_is_visible_and_does_not_invent_off(self):
        self.commands.shutdown.side_effect = ConnectionError("link lost")
        with self.assertRaisesRegex(HomeAssistantError, "Could not confirm"):
            await self.entity.async_set_hvac_mode(HVACMode.OFF)
        self.commands.read_mode.assert_not_awaited()
        self.coordinator.async_set_updated_data.assert_not_called()

    async def test_read_failure_is_visible_and_does_not_invent_off(self):
        self.commands.read_mode.side_effect = TimeoutError("read timed out")
        with self.assertRaisesRegex(HomeAssistantError, "Could not confirm"):
            await self.entity.async_turn_off()
        self.commands.shutdown.assert_awaited_once()
        self.coordinator.async_set_updated_data.assert_not_called()

    async def test_running_readback_is_not_replaced_with_optimistic_standby(self):
        self.commands.read_mode.return_value = self.original.mode
        await self.entity.async_turn_off()
        updated = self.coordinator.async_set_updated_data.call_args.args[0]
        self.assertEqual(updated.mode.mode, ModeName.RUN)

    async def test_missing_client_is_visible(self):
        self.coordinator.client = None
        with self.assertRaisesRegex(HomeAssistantError, "not connected"):
            await self.entity.async_turn_off()
        self.coordinator.async_set_updated_data.assert_not_called()

    async def test_remote_ignition_is_not_added(self):
        self.coordinator.data = GrillState(mode=GrillMode(mode=ModeName.STANDBY))
        self.assertEqual(self.entity.hvac_modes, [HVACMode.OFF])
        self.assertFalse(self.entity.supported_features & ClimateEntityFeature.TURN_ON)
        await self.entity.async_set_hvac_mode(HVACMode.HEAT)
        self.commands.shutdown.assert_not_awaited()
        self.commands.read_mode.assert_not_awaited()
        self.coordinator.async_set_updated_data.assert_not_called()

    async def test_running_entity_exposes_turn_off_without_turn_on(self):
        self.assertTrue(self.entity.supported_features & ClimateEntityFeature.TURN_OFF)
        self.assertTrue(self.entity.supported_features & ClimateEntityFeature.TARGET_TEMPERATURE)
        self.assertFalse(self.entity.supported_features & ClimateEntityFeature.TURN_ON)
