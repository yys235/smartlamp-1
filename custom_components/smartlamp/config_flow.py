from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartLampApiAuthError, SmartLampApiClient, SmartLampApiConnectionError, SmartLampApiError
from .const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_REQUEST_TIMEOUT,
    CONF_SCAN_INTERVAL,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


def _normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        normalized = f"http://{normalized}"
    return normalized


def _user_schema(
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_BASE_URL, default=defaults.get(CONF_BASE_URL, "http://127.0.0.1:8100")): str,
            vol.Optional(CONF_API_TOKEN, default=defaults.get(CONF_API_TOKEN, "")): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=300)
            ),
            vol.Optional(CONF_REQUEST_TIMEOUT, default=defaults.get(CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT)): vol.All(
                vol.Coerce(float), vol.Range(min=1, max=60)
            ),
        }
    )


class SmartLampConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            cleaned_input = dict(user_input)
            cleaned_input[CONF_BASE_URL] = _normalize_base_url(cleaned_input[CONF_BASE_URL])
            cleaned_input[CONF_API_TOKEN] = cleaned_input.get(CONF_API_TOKEN) or None
            try:
                info = await self._async_validate(cleaned_input)
            except SmartLampApiAuthError:
                errors["base"] = "invalid_auth"
            except SmartLampApiConnectionError:
                errors["base"] = "cannot_connect"
            except SmartLampApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info.instance_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"SmartLamp {info.instance_id}",
                    data=cleaned_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    async def _async_validate(self, user_input: dict[str, Any]):
        client = SmartLampApiClient(
            session=async_get_clientsession(self.hass),
            base_url=user_input[CONF_BASE_URL],
            api_token=user_input.get(CONF_API_TOKEN),
            request_timeout=user_input.get(CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT),
        )
        return await client.async_get_system_info()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return SmartLampOptionsFlow(config_entry)


class SmartLampOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {
            CONF_SCAN_INTERVAL: self.config_entry.options.get(
                CONF_SCAN_INTERVAL,
                self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ),
            CONF_REQUEST_TIMEOUT: self.config_entry.options.get(
                CONF_REQUEST_TIMEOUT,
                self.config_entry.data.get(CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT),
            ),
        }
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current[CONF_SCAN_INTERVAL]): vol.All(
                        vol.Coerce(int), vol.Range(min=5, max=300)
                    ),
                    vol.Required(CONF_REQUEST_TIMEOUT, default=current[CONF_REQUEST_TIMEOUT]): vol.All(
                        vol.Coerce(float), vol.Range(min=1, max=60)
                    ),
                }
            ),
        )
