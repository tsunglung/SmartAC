"""Config flow for SmartAC integration."""
from __future__ import annotations
import os
import json
import uuid
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .irext import AC, MODE_AUTO, SPEED_AUTO, POWER_ON, POWER_OFF

from .const import (
    CONF_MODEL,
    DOMAIN,
    CONF_BRAND,
    CONF_DEVICE,
    CONF_CONTROLLER_SERVICE,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_POWER_SENSOR,
    CONF_OK,
)

from . import CODES_AB_DIR, _LOGGER


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeKit."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self.config = {}

    async def async_step_user(self, user_input=None):
        """Choose specific domains in bridge mode."""
        errors = {}

        brands = []
        ac_index = []

        index_file_path = os.path.join(CODES_AB_DIR, "index.json")
        if not os.path.exists(index_file_path):
            _LOGGER.error("Couldn't find the index json file.")
            return self.async_abort(reason="no_index")

        with open(index_file_path) as j:
            try:
                ac_index = json.load(j)
                brands = [brand["brand_name"] for brand in ac_index]
            except Exception:
                _LOGGER.error("The index Json file is invalid")
                return self.async_abort(reason="invalid_index")

        if user_input is not None:
            self.config.update(user_input)
            for brand in ac_index:
                if brand["brand_name"] == user_input[CONF_BRAND]:
                    self.devices = {
                        device["bin"]: device["device_name"]
                        for device in brand["devices"]
                    }
                    break
            return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_BRAND): vol.In(brands)}),
            errors=errors,
        )

    async def async_step_device(self, user_input=None):
        """Choose specific domains in bridge mode."""
        # errors = {}
        if user_input is not None:
            # setup
            self.config.update(user_input)
            return await self.async_step_test_on()

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE): vol.In(self.devices),
                    vol.Required(CONF_CONTROLLER_SERVICE): cv.string,
                }
            ),
            # errors=errors,
        )

    async def async_step_test_on(self, user_input=None):
        errors = {}

        if user_input is not None:
            if user_input[CONF_OK]:
                return await self.async_step_test_off()
            else:
                self.config.update(user_input)

        # test on here
        ret = await self.async_test(
            self.config[CONF_CONTROLLER_SERVICE], self.config[CONF_DEVICE], True
        )
        errors.update(ret)

        next_device = None
        if CONF_CONTROLLER_SERVICE in errors:
            next_device = self.config[CONF_DEVICE]
        else:
            for k in self.devices.keys():
                if next_device:
                    next_device = k
                    break
                if k == self.config[CONF_DEVICE]:
                    next_device = k

        return self.async_show_form(
            step_id="test_on",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_OK, default=False): bool,
                    vol.Required(CONF_DEVICE, default=next_device): vol.In(
                        self.devices
                    ),
                    vol.Required(
                        CONF_CONTROLLER_SERVICE,
                        default=self.config[CONF_CONTROLLER_SERVICE],
                    ): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_test_off(self, user_input=None):
        errors = {}

        if user_input is not None:
            if user_input[CONF_OK]:
                return await self.async_step_other()
            else:
                self.config.update(user_input)
                return await self.async_step_test_on()

        # test off here
        ret = await self.async_test(
            self.config[CONF_CONTROLLER_SERVICE], self.config[CONF_DEVICE], False
        )
        errors.update(ret)

        next_device = None
        if CONF_CONTROLLER_SERVICE in errors:
            next_device = self.config[CONF_DEVICE]
        else:
            for k in self.devices.keys():
                if next_device:
                    next_device = k
                    break
                if k == self.config[CONF_DEVICE]:
                    next_device = k

        return self.async_show_form(
            step_id="test_off",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_OK, default=False): bool,
                    vol.Required(CONF_DEVICE, default=next_device): vol.In(
                        self.devices
                    ),
                    vol.Required(
                        CONF_CONTROLLER_SERVICE,
                        default=self.config[CONF_CONTROLLER_SERVICE],
                    ): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_test_cool(self, user_input=None):
        return self.async_show_form(
            step_id="test_cool",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=self.config[CONF_BRAND]): cv.string,
                    vol.Required(CONF_DEVICE): vol.In(
                        {
                            device["bin"]: device["device_name"]
                            for device in self.devices
                        }
                    ),
                    vol.Required(CONF_CONTROLLER_SERVICE): cv.string,
                    vol.Optional(CONF_TEMPERATURE_SENSOR): cv.string,
                    vol.Optional(CONF_HUMIDITY_SENSOR): cv.string,
                    vol.Optional(CONF_POWER_SENSOR): cv.string,
                }
            ),
            # errors=errors,
        )

    async def async_step_other(self, user_input=None):
        # errors = {}
        if user_input is not None:
            self.config[CONF_MODEL] = self.devices.get(
                self.config[CONF_DEVICE])
            self.config.update(user_input)
            return await self.async_step_setup()

        return self.async_show_form(
            step_id="other",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=self.config[CONF_BRAND]): cv.string,
                    vol.Optional(CONF_TEMPERATURE_SENSOR): cv.string,
                    vol.Optional(CONF_HUMIDITY_SENSOR): cv.string,
                    vol.Optional(CONF_POWER_SENSOR): cv.string,
                }
            ),
            last_step=True
            # errors=errors,
        )

    async def async_step_setup(self):
        unique_id = str(uuid.uuid4())
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        self.config[CONF_UNIQUE_ID] = unique_id

        return self.async_create_entry(title=self.config[CONF_NAME], data=self.config)

    async def async_test(self, service_id, device_file, power_on):
        device_bin_path = os.path.join(CODES_AB_DIR, device_file)
        if not os.path.exists(device_bin_path):
            _LOGGER.error(
                "Couldn't find the device bin file.(%s)", device_file)
            return {CONF_DEVICE: "no_device_file"}

        with open(device_bin_path, "rb") as j:
            try:
                ac = AC(j.read())
                all_modes = ac.get_supported_mode()
                mode = MODE_AUTO if MODE_AUTO in all_modes else all_modes[0]
                all_speed = ac.get_supported_wind_speed(mode)
                speed = SPEED_AUTO if not all_speed or SPEED_AUTO in all_speed else all_speed[
                    0]
                all_temperature = ac.get_temperature_range(mode)
                temperature = 26 if not all_temperature or 26 in all_temperature else all_temperature[
                    0]
                power = POWER_ON if power_on else POWER_OFF
                _, raw = ac.ir_decode(power, temperature, mode, speed)
            except Exception:
                _LOGGER.error("The device bin file is invalid")
                return {CONF_DEVICE: "invalid_device_file"}

        service_domain = "esphome"

        service = service_id.split(".")
        if len(service) >= 2:
            service_domain = service[0]
            service_id = service[1]

        if not self.hass.services.has_service(service_domain, service_id):
            return {CONF_CONTROLLER_SERVICE: "no_such_service"}

        try:
            service_data = {"command": raw}
            await self.hass.services.async_call(
                service_domain, service_id, service_data
            )
            return {}
        except Exception:
            _LOGGER.error("call service failed")
            return {CONF_CONTROLLER_SERVICE: "call_service_failed"}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for homekit."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.config = dict(config_entry.data)
        # self.options = dict(config_entry.options)

        with open(os.path.join(COMPONENT_ABS_DIR, "index.json")) as j:
            try:
                self.ac_index = json.load(j)
            except Exception:
                _LOGGER.error("The device Json file is invalid")
                return

        for brand in self.ac_index:
            if brand["brand_name"] == self.config.get(CONF_BRAND):
                self.devices = brand["devices"]
                break

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        # errors = {}
        if user_input is not None:
            # self.config_entry.data.update(user_input)
            self.config.update(user_input)
            # self.options.update(user_input)
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=self.config
            )
            return self.async_create_entry(title="", data=self.config)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    # vol.Required(CONF_NAME, default=self.config.get(CONF_NAME)): cv.string,
                    vol.Required(
                        CONF_CONTROLLER_SERVICE,
                        default=self.config.get(CONF_CONTROLLER_SERVICE),
                    ): cv.string,
                    vol.Optional(
                        CONF_TEMPERATURE_SENSOR,
                        default=self.config.get(CONF_TEMPERATURE_SENSOR, ""),
                    ): cv.string,
                    vol.Optional(
                        CONF_HUMIDITY_SENSOR,
                        default=self.config.get(CONF_HUMIDITY_SENSOR, ""),
                    ): cv.string,
                    vol.Optional(
                        CONF_POWER_SENSOR,
                        default=self.config.get(CONF_POWER_SENSOR, ""),
                    ): cv.string,
                }
            ),
            # errors=errors,
        )
