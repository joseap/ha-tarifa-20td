"""Create and update configuration flows."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Self

from typing_extensions import override
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    CONF_ALQUILER_CONTADOR,
    CONF_BONO_SOCIAL,
    CONF_DIARY_COST,
    CONF_IMPUESTO_ELECTRICO,
    CONF_IVA,
    CONF_OTROS,
    CONF_P1,
    CONF_P2,
    CONF_P3,
    CONF_P4,
    CONF_P5,
    CONF_P6,
    CONF_PRECIO_POTENCIA_PUNTA,
    CONF_PRECIO_POTENCIA_VALLE,
    CONF_TARIFF,
    DEFAULT_IMPUESTO_ELECTRICO,
    DEFAULT_IVA,
    DOMAIN,
    TARIFF_20,
    TARIFF_30,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)


def _calculate_diary_cost(data: dict[str, Any]) -> float:
    """Calculate fixed daily costs from configured values."""
    bono_social = float(data.get(CONF_BONO_SOCIAL, 0))
    potencia_punta = float(data.get(CONF_PRECIO_POTENCIA_PUNTA, 0))
    potencia_valle = float(data.get(CONF_PRECIO_POTENCIA_VALLE, 0))
    alquiler_contador = float(data.get(CONF_ALQUILER_CONTADOR, 0))

    impuesto_electrico = float(data.get(CONF_IMPUESTO_ELECTRICO, DEFAULT_IMPUESTO_ELECTRICO)) / 100
    iva = float(data.get(CONF_IVA, DEFAULT_IVA)) / 100

    # Se calcula primero:
    # base_fija = ((bono + valle + punta) * impuesto_electrico) + alquiler_contador
    base_fija = ((bono_social + potencia_valle + potencia_punta) * impuesto_electrico) + alquiler_contador

    # Y luego:
    # return base_fija * iva
    return base_fija * iva


def _fixed_cost_schema() -> dict:
    """Return schema fields for fixed cost breakdown and taxes."""
    return {
        vol.Required(CONF_BONO_SOCIAL): NumberSelector(
            NumberSelectorConfig(
                min=0,
                step="any",
                unit_of_measurement="€/día",
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_ALQUILER_CONTADOR): NumberSelector(
            NumberSelectorConfig(
                min=0,
                step="any",
                unit_of_measurement="€/día",
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_PRECIO_POTENCIA_PUNTA): NumberSelector(
            NumberSelectorConfig(
                min=0,
                step="any",
                unit_of_measurement="€/día",
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_PRECIO_POTENCIA_VALLE): NumberSelector(
            NumberSelectorConfig(
                min=0,
                step="any",
                unit_of_measurement="€/día",
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_OTROS): NumberSelector(
            NumberSelectorConfig(
                min=0,
                step="any",
                unit_of_measurement="€/día",
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_IMPUESTO_ELECTRICO, default=DEFAULT_IMPUESTO_ELECTRICO): NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=100,
                step="any",
                unit_of_measurement="%",
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_IVA, default=DEFAULT_IVA): NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=100,
                step="any",
                unit_of_measurement="%",
                mode=NumberSelectorMode.BOX,
            )
        ),
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Tariff TD."""

    VERSION = 2
    tariff = TARIFF_20

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionFlowHandler:
        return OptionFlowHandler()

    @override
    def is_matching(self, other_flow: Self) -> bool:
        return False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Config flow of Tariff TD."""
        if user_input is not None:
            self.tariff = user_input[CONF_TARIFF]
            if self.tariff == TARIFF_30:
                return await self.async_step_tariff30()

            return await self.async_step_tariff20()

        schema = vol.Schema(
            {
                vol.Required(CONF_TARIFF): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=TARIFF_20, label="Tarifa 2.0 TD (3 periodos)"),
                            SelectOptionDict(value=TARIFF_30, label="Tarifa 3.0 TD (6 periodos)"),
                        ]
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_tariff20(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Form configuration for Tariff 2.0 TD."""
        if user_input is not None:
            user_input[CONF_TARIFF] = self.tariff
            user_input[CONF_DIARY_COST] = _calculate_diary_cost(user_input)
            return self.async_create_entry(data=user_input, title="Tarifa TD")

        schema = {
            vol.Required(CONF_P1): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P2): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P3): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            **_fixed_cost_schema(),
        }

        return self.async_show_form(step_id="tariff20", data_schema=vol.Schema(schema))

    async def async_step_tariff30(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Form configuration for Tariff 3.0 TD."""
        if user_input is not None:
            user_input[CONF_TARIFF] = self.tariff
            user_input[CONF_DIARY_COST] = _calculate_diary_cost(user_input)
            return self.async_create_entry(data=user_input, title="Tarifa TD")

        schema = {
            vol.Required(CONF_P1): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P2): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P3): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P4): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P5): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P6): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            **_fixed_cost_schema(),
        }

        return self.async_show_form(step_id="tariff30", data_schema=vol.Schema(schema))


class OptionFlowHandler(config_entries.OptionsFlow):
    """Reconfigure Flow for Tariff TD."""

    tariff = TARIFF_20

    @property
    def config_entry(self):
        return self.hass.config_entries.async_get_entry(self.handler)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Tariff TD selector form."""
        if user_input is not None:
            self.tariff = user_input[CONF_TARIFF]
            if self.tariff == TARIFF_30:
                return await self.async_step_tariff30()

            return await self.async_step_tariff20()

        tariff = self.config_entry.data.get(CONF_TARIFF, TARIFF_20)

        schema = vol.Schema(
            {
                vol.Required(CONF_TARIFF, default=tariff): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=TARIFF_20, label="Tarifa 2.0 TD (3 periodos)"),
                            SelectOptionDict(value=TARIFF_30, label="Tarifa 3.0 TD (6 periodos)"),
                        ]
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_tariff20(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Form configuration for Tariff 2.0 TD."""
        if user_input is not None:
            user_input[CONF_TARIFF] = self.tariff
            user_input[CONF_DIARY_COST] = _calculate_diary_cost(user_input)
            return self.async_create_entry(data=user_input, title="Tarifa TD")

        p1 = self.config_entry.data.get(CONF_P1, 0)
        p2 = self.config_entry.data.get(CONF_P2, 0)
        p3 = self.config_entry.data.get(CONF_P3, 0)
        bono_social = self.config_entry.data.get(CONF_BONO_SOCIAL, 0)
        alquiler_contador = self.config_entry.data.get(CONF_ALQUILER_CONTADOR, 0)
        potencia_punta = self.config_entry.data.get(CONF_PRECIO_POTENCIA_PUNTA, 0)
        potencia_valle = self.config_entry.data.get(CONF_PRECIO_POTENCIA_VALLE, 0)
        otros = self.config_entry.data.get(CONF_OTROS, 0)
        impuesto_electrico = self.config_entry.data.get(CONF_IMPUESTO_ELECTRICO, DEFAULT_IMPUESTO_ELECTRICO)
        iva = self.config_entry.data.get(CONF_IVA, DEFAULT_IVA)

        schema = {
            vol.Required(CONF_P1, default=p1): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P2, default=p2): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P3, default=p3): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_BONO_SOCIAL, default=bono_social): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    step="any",
                    unit_of_measurement="€/día",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_ALQUILER_CONTADOR, default=alquiler_contador): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    step="any",
                    unit_of_measurement="€/día",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_PRECIO_POTENCIA_PUNTA, default=potencia_punta): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    step="any",
                    unit_of_measurement="€/día",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_PRECIO_POTENCIA_VALLE, default=potencia_valle): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    step="any",
                    unit_of_measurement="€/día",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_OTROS, default=otros): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    step="any",
                    unit_of_measurement="€/día",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_IMPUESTO_ELECTRICO, default=impuesto_electrico): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100,
                    step="any",
                    unit_of_measurement="%",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_IVA, default=iva): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100,
                    step="any",
                    unit_of_measurement="%",
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }

        return self.async_show_form(step_id="tariff20", data_schema=vol.Schema(schema))

    async def async_step_tariff30(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Form configuration for Tariff 3.0 TD."""
        if user_input is not None:
            user_input[CONF_TARIFF] = self.tariff
            user_input[CONF_DIARY_COST] = _calculate_diary_cost(user_input)
            return self.async_create_entry(data=user_input, title="Tarifa TD")

        p1 = self.config_entry.data.get(CONF_P1, 0)
        p2 = self.config_entry.data.get(CONF_P2, 0)
        p3 = self.config_entry.data.get(CONF_P3, 0)
        p4 = self.config_entry.data.get(CONF_P4, 0)
        p5 = self.config_entry.data.get(CONF_P5, 0)
        p6 = self.config_entry.data.get(CONF_P6, 0)
        bono_social = self.config_entry.data.get(CONF_BONO_SOCIAL, 0)
        alquiler_contador = self.config_entry.data.get(CONF_ALQUILER_CONTADOR, 0)
        potencia_punta = self.config_entry.data.get(CONF_PRECIO_POTENCIA_PUNTA, 0)
        potencia_valle = self.config_entry.data.get(CONF_PRECIO_POTENCIA_VALLE, 0)
        otros = self.config_entry.data.get(CONF_OTROS, 0)
        impuesto_electrico = self.config_entry.data.get(CONF_IMPUESTO_ELECTRICO, DEFAULT_IMPUESTO_ELECTRICO)
        iva = self.config_entry.data.get(CONF_IVA, DEFAULT_IVA)

        schema = {
            vol.Required(CONF_P1, default=p1): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P2, default=p2): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P3, default=p3): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P4, default=p4): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P5, default=p5): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_P6, default=p6): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=1,
                    step="any",
                    unit_of_measurement="€/kWh",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_BONO_SOCIAL, default=bono_social): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    step="any",
                    unit_of_measurement="€/día",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_ALQUILER_CONTADOR, default=alquiler_contador): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    step="any",
                    unit_of_measurement="€/día",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_PRECIO_POTENCIA_PUNTA, default=potencia_punta): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    step="any",
                    unit_of_measurement="€/día",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_PRECIO_POTENCIA_VALLE, default=potencia_valle): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    step="any",
                    unit_of_measurement="€/día",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_OTROS, default=otros): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    step="any",
                    unit_of_measurement="€/día",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_IMPUESTO_ELECTRICO, default=impuesto_electrico): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100,
                    step="any",
                    unit_of_measurement="%",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_IVA, default=iva): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100,
                    step="any",
                    unit_of_measurement="%",
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }

        return self.async_show_form(step_id="tariff30", data_schema=vol.Schema(schema))
