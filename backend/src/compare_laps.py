"""
Milestone 1: load one session, pick two drivers' fastest laps,
print lap + sector times, and calculate the deltas.

Run from the project root:
    python -m src.compare_laps
    python -m src.compare_laps --year 2024 --event Silverstone --session Q --a HAM --b RUS
"""
import argparse
from pathlib import Path

import fastf1
import pandas as pd

CACHE_DIR = Path("cache")


def load_session(year: int, event: str, session_type: str):
    """Load a session (timing only for now, no telemetry yet)."""
    CACHE_DIR.mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))
    session = fastf1.get_session(year, event, session_type)
    session.load(telemetry=False, weather=False, messages=False)
    return session


def fastest_lap(session, driver: str) -> pd.Series:
    """Return a driver's fastest valid lap, or raise a clear error."""
    laps = session.laps.pick_drivers(driver)
    if laps.empty:
        available = sorted(session.laps["Driver"].unique())
        raise ValueError(f"No laps found for '{driver}'. Available drivers: {available}")
    lap = laps.pick_fastest()
    if lap is None or pd.isna(lap["LapTime"]):
        raise ValueError(f"{driver} has no valid timed lap in this session.")
    return lap


def fmt(td) -> str:
    """Format a Timedelta as M:SS.mmm (or SS.mmm for sectors)."""
    if pd.isna(td):
        return "n/a"
    total = td.total_seconds()
    minutes, seconds = divmod(total, 60)
    return f"{int(minutes)}:{seconds:06.3f}" if minutes else f"{seconds:.3f}"


def compare(lap_a: pd.Series, lap_b: pd.Series) -> pd.DataFrame:
    """Build a table of lap/sector times and the delta (B minus A)."""
    rows = []
    for label, col in [("Sector 1", "Sector1Time"), ("Sector 2", "Sector2Time"),
                       ("Sector 3", "Sector3Time"), ("Lap", "LapTime")]:
        a, b = lap_a[col], lap_b[col]
        delta = (b - a).total_seconds() if pd.notna(a) and pd.notna(b) else float("nan")
        rows.append({"Segment": label, lap_a["Driver"]: fmt(a),
                     lap_b["Driver"]: fmt(b), "Delta (s)": round(delta, 3)})
    return pd.DataFrame(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, default=2024)
    p.add_argument("--event", default="Silverstone")
    p.add_argument("--session", default="Q")
    p.add_argument("--a", default="HAM")
    p.add_argument("--b", default="RUS")
    args = p.parse_args()

    session = load_session(args.year, args.event, args.session)
    print(f"\n{session.event['EventName']} {args.year} - {session.name}")
    print(f"Drivers in session: {sorted(session.laps['Driver'].unique())}\n")

    lap_a = fastest_lap(session, args.a)
    lap_b = fastest_lap(session, args.b)
    table = compare(lap_a, lap_b)
    print(table.to_string(index=False))

    gap = table.iloc[-1]["Delta (s)"]
    leader = args.a if gap > 0 else args.b
    print(f"\n{leader} was faster by {abs(gap):.3f}s on their best lap.")
    print("(Delta = driver B minus driver A; positive means A was quicker.)")


if __name__ == "__main__":
    main()