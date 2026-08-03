"""Tests for the tariff CSV parsing logic in the coordinator."""

from datetime import datetime
from unittest.mock import patch

from custom_components.tarif_edf.const import (
    CONTRACT_TYPE_BASE,
    CONTRACT_TYPE_HPHC,
    CONTRACT_TYPE_TEMPO,
)
from custom_components.tarif_edf.coordinator import TarifEdfDataUpdateCoordinator


def _parse(csv_text: str, power: str, contract_type: str):
    # _parse_tariff_csv never touches `self`, so it can be called unbound.
    return TarifEdfDataUpdateCoordinator._parse_tariff_csv(
        None, csv_text.encode("utf-8"), power, contract_type
    )


@patch("custom_components.tarif_edf.coordinator.dt_util.now")
def test_parse_base_csv(mock_now):
    mock_now.return_value = datetime(2026, 6, 1)
    csv_content = (
        "DATE_DEBUT;DATE_FIN;PUISSANCE;PART_FIXE_TTC;PART_VARIABLE_TTC\n"
        "01/01/2026;;6;120,00;0,2000\n"
        "01/01/2026;;9;150,00;0,2100\n"
    )
    result = _parse(csv_content, "6", CONTRACT_TYPE_BASE)
    assert result["base_variable_ttc"] == 0.2
    assert result["base_fixe_ttc"] == 120.0
    assert result["base_abonnement_ttc"] == 10.0


@patch("custom_components.tarif_edf.coordinator.dt_util.now")
def test_parse_hphc_csv(mock_now):
    mock_now.return_value = datetime(2026, 6, 1)
    csv_content = (
        "DATE_DEBUT;DATE_FIN;PUISSANCE;PART_FIXE_TTC;PART_VARIABLE_HC_TTC;PART_VARIABLE_HP_TTC\n"
        "01/01/2026;;6;144,00;0,1500;0,2200\n"
    )
    result = _parse(csv_content, "6", CONTRACT_TYPE_HPHC)
    assert result["hphc_variable_hc_ttc"] == 0.15
    assert result["hphc_variable_hp_ttc"] == 0.22
    assert result["hphc_abonnement_ttc"] == 12.0


@patch("custom_components.tarif_edf.coordinator.dt_util.now")
def test_parse_tempo_csv(mock_now):
    mock_now.return_value = datetime(2026, 6, 1)
    csv_content = (
        "DATE_DEBUT;DATE_FIN;P_SOUSCRITE;PART_FIXE_TTC;"
        "PART_VARIABLE_HCBleu_TTC;PART_VARIABLE_HPBleu_TTC;"
        "PART_VARIABLE_HCBlanc_TTC;PART_VARIABLE_HPBlanc_TTC;"
        "PART_VARIABLE_HCRouge_TTC;PART_VARIABLE_HPRouge_TTC\n"
        "01/01/2026;;9;96,00;0,1000;0,1500;0,1200;0,1700;0,1400;0,6500\n"
    )
    result = _parse(csv_content, "9", CONTRACT_TYPE_TEMPO)
    assert result["tempo_variable_hc_bleu_ttc"] == 0.10
    assert result["tempo_variable_hp_bleu_ttc"] == 0.15
    assert result["tempo_variable_hc_rouge_ttc"] == 0.14
    assert result["tempo_variable_hp_rouge_ttc"] == 0.65
    assert result["tempo_abonnement_ttc"] == 8.0


@patch("custom_components.tarif_edf.coordinator.dt_util.now")
def test_parse_returns_none_when_no_matching_power(mock_now):
    mock_now.return_value = datetime(2026, 6, 1)
    csv_content = (
        "DATE_DEBUT;DATE_FIN;PUISSANCE;PART_FIXE_TTC;PART_VARIABLE_TTC\n"
        "01/01/2026;;9;150,00;0,2100\n"
    )
    assert _parse(csv_content, "6", CONTRACT_TYPE_BASE) is None


@patch("custom_components.tarif_edf.coordinator.dt_util.now")
def test_parse_skips_expired_tariff(mock_now):
    mock_now.return_value = datetime(2026, 6, 1)
    csv_content = (
        "DATE_DEBUT;DATE_FIN;PUISSANCE;PART_FIXE_TTC;PART_VARIABLE_TTC\n"
        "01/01/2020;31/12/2020;6;100,00;0,1500\n"
    )
    assert _parse(csv_content, "6", CONTRACT_TYPE_BASE) is None


@patch("custom_components.tarif_edf.coordinator.dt_util.now")
def test_parse_picks_most_recent_applicable_tariff(mock_now):
    mock_now.return_value = datetime(2026, 6, 1)
    csv_content = (
        "DATE_DEBUT;DATE_FIN;PUISSANCE;PART_FIXE_TTC;PART_VARIABLE_TTC\n"
        "01/01/2024;;6;100,00;0,1500\n"
        "01/01/2025;;6;120,00;0,2000\n"
        "01/01/2027;;6;999,00;0,9999\n"  # not yet effective, must be ignored
    )
    result = _parse(csv_content, "6", CONTRACT_TYPE_BASE)
    assert result["base_variable_ttc"] == 0.2
