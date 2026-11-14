"""Adapter: PSI-69 FLEX (Flame Extinguishment Experiment) - liquid droplets, ISS CIR/MDCA."""
from etl.core.common import (Run, MMHG_TO_KPA, clean_text, fmt, new_run, parse_mdy, parse_num,
                             parse_time, read_raw_table)

SOURCE_ID = "PSI-69"
TABLE = "PSI-69_FLEX/PSI-69_Experimental table_FLEX.csv"
ENCODING = "cp1252"  # file uses Windows en-dash (0x96) as a blank marker

C_TEST, C_IDENT, C_DATE, C_TIME, C_FUEL = "FLEX Test #", "FLEX Identifier", "Test Date", "Test GMT", "Fuel"
C_P = "Ambient pressure; mmHg"
C_O2 = "O initial ambient composition; mole fraction"
C_N2 = "N initial ambient composition; mole fraction"
C_CO = "CO initial ambient composition; mole fraction"
C_HE = "He initial ambient composition; mole fraction"
C_END = "Test end"


def parse() -> list[Run]:
    rows, headers, sha = read_raw_table(TABLE, ENCODING)
    idents = [clean_text(r[C_IDENT]) for r in rows]
    runs = []
    for i, row in enumerate(rows, start=1):
        test_no = clean_text(row[C_TEST])
        time, time_bad = parse_time(row[C_TIME])
        o2, o2_reason = parse_num(row[C_O2])
        p, p_reason = parse_num(row[C_P])
        d = new_run(
            SOURCE_ID, "FLEX", f"FLEX-{int(test_no):03d}", f"data/raw/{TABLE}", sha, i,
            native_test_id=test_no, domain="liquid_droplet", platform="ISS", gravity_regime="microgravity",
            test_date=parse_mdy(row[C_DATE]) or "", test_date_raw=clean_text(row[C_DATE]),
            test_time_gmt=time or "",
            fuel_raw=clean_text(row[C_FUEL]), fuel=clean_text(row[C_FUEL]).lower(),
            o2_vol_pct=fmt(o2 * 100 if o2 is not None else None), o2_basis="initial" if o2 is not None else "",
            o2_missing_reason=o2_reason or "", o2_raw=clean_text(row[C_O2]), o2_raw_unit="mole fraction",
            pressure_kpa=fmt(p * MMHG_TO_KPA if p is not None else None),
            pressure_missing_reason=p_reason or "", pressure_raw=clean_text(row[C_P]), pressure_raw_unit="mmHg",
            flow_missing_reason="unavailable_in_source",  # droplets burn in quiescent ambient; no flow column
            outcome_raw=clean_text(row[C_END]),
        )
        r = Run(d, raw_cells=tuple(row[h] for h in headers))
        if time_bad:
            r.flag("time_unparsed")
        if idents.count(clean_text(row[C_IDENT])) > 1:
            r.flag("identifier_reused")
        fracs = [parse_num(row[c])[0] for c in (C_O2, C_N2, C_CO, C_HE)]
        if all(f is not None for f in fracs) and abs(sum(fracs) - 1) > 0.01 + 1e-9:  # tolerance per contract; 1e-9 absorbs float error
            r.flag("gas_sum_off")

        r.measure(row, C_IDENT, "flex_identifier", None, numeric=False)
        r.measure(row, C_N2, "n2_initial_mole_fraction", "mole fraction")
        r.measure(row, C_CO, "co_initial_mole_fraction", "mole fraction")  # CO vs CO2 unconfirmed: issue I-002
        r.measure(row, C_HE, "he_initial_mole_fraction", "mole fraction")
        r.measure(row, "Droplet initial diameter; mm", "droplet_initial_diameter", "mm")
        r.measure(row, "Visible flame extinction diameter; mm", "flame_extinction_diameter", "mm")
        r.measure(row, "Burning rate; mm", "burning_rate", None)  # unit undefined in source: issue I-001
        r.measure(row, "Burn time; s", "burn_time", "s")
        r.measure(row, C_END, "test_end", None, numeric=False)
        runs.append(r)
    return runs
