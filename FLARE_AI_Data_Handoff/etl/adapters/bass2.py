"""Adapter: PSI-25 BASS-II (Burning and Suppression of Solids II) - solid fuels, ISS MSG."""
import re

from etl.core.common import Run, clean_text, fmt, new_run, parse_mdy, parse_num, read_raw_table

SOURCE_ID = "PSI-25"
TABLE = "PSI-25_BASS-II/PSI-25_Experimental table_BASS-II.csv"
ENCODING = "utf-8-sig"

C_O2I = "Calibrated  initial O2 % by vol "   # raw header has a double space and trailing space
C_O2F = "Calibrated final O2 % by vol"
C_FUEL = "Fuel Sample Material"
C_AIR = "Air display"

# Material keywords confirmed in the cell or in BASS-II data FAQ.docx (issue I-019 resolved:
# Bhattacharjee films, Olson/Fernandez-Pello rods, and T'ien's 4 cm spherical section are all PMMA).
MATERIALS = [
    ("pmma", "PMMA"), ("rod", "PMMA"), ("film", "PMMA"), ("micron", "PMMA"), ("spherical section", "PMMA"),
    ("sibal", "SIBAL"), ("nomex", "Nomex"), ("wax candle", "wax candle"),
]


def normalise_fuel(text: str) -> str:
    low = text.lower()
    for key, label in MATERIALS:
        if key in low:
            return label
    return low  # e.g. '1/4" black rod': material not stated, so not guessed (issue I-019)


def parse() -> list[Run]:
    rows, headers, sha = read_raw_table(TABLE, ENCODING)
    runs = []
    for i, row in enumerate(rows, start=1):
        test_no = clean_text(row["Test #"])
        fuel_raw = clean_text(row[C_FUEL])
        o2, o2_reason = parse_num(row[C_O2I])
        air_val, air_reason = parse_num(row[C_AIR])
        d = new_run(
            SOURCE_ID, "BASS-II", test_no, f"data/raw/{TABLE}", sha, i,
            native_test_id=test_no, domain="solid", platform="ISS", gravity_regime="microgravity",
            test_date=parse_mdy(row["Date"]) or "", test_date_raw=clean_text(row["Date"]),
            # 'GMT' column is day-of-year, not a clock time -> kept as a measurement only
            fuel_raw=fuel_raw, fuel=normalise_fuel(fuel_raw), fuel_detail=fuel_raw,
            o2_vol_pct=fmt(o2), o2_basis="initial" if o2 is not None else "",  # basis awaits Malak (contract s4)
            o2_missing_reason=o2_reason or "", o2_raw=clean_text(row[C_O2I]), o2_raw_unit="% by vol",
            pressure_missing_reason="unavailable_in_source",
            flow_basis="tunnel air velocity (from instrument display)",
            # A single numeric air display could be converted via Fan calibration data.xlsx once approved (I-006/7)
            flow_missing_reason="pending_review" if air_val is not None else (air_reason or "not_reported"),
            flow_raw=clean_text(row[C_AIR]), flow_raw_unit="air display (instrument units)",
        )
        r = Run(d, raw_cells=tuple(row[h] for h in headers))
        if d["test_date"] and not d["test_date"].startswith("2014-"):
            r.flag("date_year_typo_in_source")  # O20-O22 (2016) and T9, T18 (2018); GMT confirms 2014 (I-024)
        r.measure(row, "PI", "principal_investigator", None, numeric=False)
        r.measure(row, "GMT", "gmt_day_of_year", "day of year")
        r.measure(row, "Sample #", "sample_number", "1")
        r.measure(row, "Flow restrictor", "flow_restrictor_count", "1")
        r.measure(row, "Fan display", "fan_display", None, numeric=False)
        r.measure(row, C_AIR, "air_display", None, numeric=False)
        r.measure(row, "Radiometer gain   (1000   250   50   10)", "radiometer_gain", "1")
        r.measure(row, "Total Frames Shot", "total_frames_shot", "1")
        r.measure(row, C_O2F, "o2_final_vol_pct", "% by vol")
        r.measure(row, "Initial CO2 % by vol", "co2_initial_vol_pct", "% by vol")
        r.measure(row, "Final CO2 % by vol", "co2_final_vol_pct", "% by vol")
        r.measure(row, "Initial CO (ppm)", "co_initial_ppm", "ppm")
        r.measure(row, "Final CO (ppm)", "co_final_ppm", "ppm")
        # Negative gas readings are sensor artifacts (issue I-010): blank the number, keep the raw text.
        for m in r.measurements:
            if m["unit"] in ("ppm", "% by vol") and m["value_num"] and float(m["value_num"]) < 0:
                m["value_num"], m["missing_reason"] = "", "invalid_value"
                r.flag("negative_gas_reading")
        runs.append(r)
    return runs
