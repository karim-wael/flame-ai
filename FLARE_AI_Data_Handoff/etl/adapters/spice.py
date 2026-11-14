"""Adapter: PSI-107 SPICE (Smoke Point In Co-flow Experiment) - gas jet flames, ISS MSG."""
from datetime import date, timedelta
import re

from etl.core.common import Run, clean_text, fmt, new_run, parse_num, parse_time, read_raw_table

SOURCE_ID = "PSI-107"
TABLE = "PSI-107_SPICE/PSI-107_Experimental table_Spice.csv"
ENCODING = "utf-8-sig"
FLIGHT_YEAR = 2009  # Confirmed by SPICE Final Report p.13 & Dotson thesis p.22 (Feb 14 - Jun 23, 2009)

C_DAY, C_IGN, C_OFF = "GMT date", "GMT ignition", "GMT  Flame Off "
C_FUEL, C_NOZ, C_AIR = "Fuel", "Nozzle (mm)", "Air Rate (cm/s)"
C_SCCM, C_MGS, C_HC = "Fuel Rate (sccm)", "Fuel Rate (mg/s)", "HC Fuel Rate (mg/s)"


def normalise_fuel(text: str) -> str:
    return re.sub(r"(\d+)\s*%\s*", r"\1% ", text.lower()).strip()  # '75 % Propylene' -> '75% propylene'


def parse() -> list[Run]:
    rows, headers, sha = read_raw_table(TABLE, ENCODING)
    runs = []
    for i, row in enumerate(rows, start=1):
        day = clean_text(row[C_DAY])
        time, time_bad = parse_time(row[C_IGN])
        key_time = time.replace(":", "") if time else "NOTIME"
        fuel_raw = clean_text(row[C_FUEL])
        air, air_reason = parse_num(row[C_AIR])
        iso_date = (date(FLIGHT_YEAR, 1, 1) + timedelta(days=int(day) - 1)).isoformat() if day.isdigit() else ""
        # Synthetic key (no run ID in source): day-of-year + ignition time + row ordinal. Stable because raw is frozen.
        d = new_run(
            SOURCE_ID, "SPICE", f"D{day}-{key_time}-R{i:03d}", f"data/raw/{TABLE}", sha, i,
            domain="gas_jet", platform="ISS", gravity_regime="microgravity",
            test_date=iso_date, test_date_raw=day,  # year 2009 confirmed in SPICE Final Report p.13 (I-014)
            test_time_gmt=time or "",
            fuel_raw=fuel_raw, fuel=normalise_fuel(fuel_raw),
            o2_missing_reason="unavailable_in_source", pressure_missing_reason="unavailable_in_source",
            flow_cm_s=fmt(air), flow_basis="co-flow air velocity", flow_missing_reason=air_reason or "",
            flow_raw=clean_text(row[C_AIR]), flow_raw_unit="cm/s",
        )
        r = Run(d, raw_cells=tuple(row[h] for h in headers))
        if time_bad:
            r.flag("time_unparsed")
        r.near_key = (day, time, normalise_fuel(fuel_raw), clean_text(row[C_NOZ]))
        r.near_nums = tuple(parse_num(row[c])[0] for c in (C_SCCM, C_MGS, C_HC, C_AIR))

        r.measure(row, C_DAY, "gmt_day_of_year", "day of year")
        r.measure(row, C_IGN, "gmt_ignition_raw", None, numeric=False)
        r.measure(row, C_OFF, "gmt_flame_off_raw", None, numeric=False)
        r.measure(row, C_NOZ, "nozzle_diameter", "mm")
        r.measure(row, C_SCCM, "fuel_rate_sccm", "sccm")
        r.measure(row, C_MGS, "fuel_rate_mg_s", "mg/s")
        r.measure(row, C_HC, "hc_fuel_rate_mg_s", "mg/s")
        runs.append(r)
    return runs
