"""Tests for the Tarif EDF config and options flow."""

import re

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.tarif_edf.const import (
    DOMAIN,
    TARIF_BASE_URL,
    TARIF_HPHC_URL,
    TARIF_TEMPO_URL,
    TEMPO_COLOR_API_URL,
)

BASE_CSV = (
    "DATE_DEBUT;DATE_FIN;PUISSANCE;PART_FIXE_TTC;PART_VARIABLE_TTC\n"
    "01/01/2020;;6;120,00;0,2000\n"
)
HPHC_CSV = (
    "DATE_DEBUT;DATE_FIN;PUISSANCE;PART_FIXE_TTC;PART_VARIABLE_HC_TTC;PART_VARIABLE_HP_TTC\n"
    "01/01/2020;;9;144,00;0,1500;0,2200\n"
)
TEMPO_CSV = (
    "DATE_DEBUT;DATE_FIN;P_SOUSCRITE;PART_FIXE_TTC;"
    "PART_VARIABLE_HCBleu_TTC;PART_VARIABLE_HPBleu_TTC;"
    "PART_VARIABLE_HCBlanc_TTC;PART_VARIABLE_HPBlanc_TTC;"
    "PART_VARIABLE_HCRouge_TTC;PART_VARIABLE_HPRouge_TTC\n"
    "01/01/2020;;9;96,00;0,1000;0,1500;0,1200;0,1700;0,1400;0,6500\n"
)


@pytest.mark.asyncio
async def test_base_contract_flow(hass, aioclient_mock):
    aioclient_mock.get(TARIF_BASE_URL, text=BASE_CSV)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "contract"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"contract_type": "base"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "power"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"contract_power": "6"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"contract_type": "base", "contract_power": "6"}
    assert result["options"] == {}
    assert result["result"].state is config_entries.ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_hphc_contract_flow_asks_for_offpeak_hours(hass, aioclient_mock):
    aioclient_mock.get(TARIF_HPHC_URL, text=HPHC_CSV)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"contract_type": "hphc"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"contract_power": "9"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "offpeak_hours"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"off_peak_hours_ranges": "22:00-06:00"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {"off_peak_hours_ranges": "22:00-06:00"}
    assert result["result"].state is config_entries.ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_tempo_contract_flow_skips_offpeak_hours_step(hass, aioclient_mock):
    aioclient_mock.get(TARIF_TEMPO_URL, text=TEMPO_CSV)
    aioclient_mock.get(
        re.compile(rf"^{re.escape(TEMPO_COLOR_API_URL)}/.*"),
        json={"dateJour": "2026-06-01", "codeJour": 1},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"contract_type": "tempo"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"contract_power": "9"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"contract_type": "tempo", "contract_power": "9"}
    assert result["options"] == {}
    assert result["result"].state is config_entries.ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_options_flow_defaults_offpeak_hours_for_tempo(hass, aioclient_mock):
    aioclient_mock.get(TARIF_TEMPO_URL, text=TEMPO_CSV)
    aioclient_mock.get(
        re.compile(rf"^{re.escape(TEMPO_COLOR_API_URL)}/.*"),
        json={"dateJour": "2026-06-01", "codeJour": 1},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"contract_type": "tempo"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"contract_power": "9"}
    )
    await hass.async_block_till_done()
    entry = result["result"]

    options_result = await hass.config_entries.options.async_init(entry.entry_id)
    assert options_result["type"] is FlowResultType.FORM
    assert options_result["data_schema"]({}) == {
        "refresh_interval": 1,
        "off_peak_hours_ranges": "22:00-06:00",
    }

