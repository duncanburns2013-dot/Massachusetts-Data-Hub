"""Register test. Prints and exits 0 on pass, 1 on fail. Stdlib only."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.refresh.register import load_sources

try:
    srcs = load_sources(REPO / "data" / "sources.json")
    by_id = {s.id: s for s in srcs}
    assert "census_acs1_ma_income" in by_id
    acs = by_id["census_acs1_ma_income"]
    assert acs.probe == "census_acs1"
    assert acs.held_period == "2025"
    assert "affordability-dashboard.html" in acs.targets
    doi = by_id["doi_merged_market_rates"]
    assert doi.multi_stage is True
    assert doi.final_tell  # must say how to recognise a final stage
    # apply flag: only ACS is written by the loop; BEA and DOI are survey-only
    assert acs.apply is True
    assert by_id["bea_rpp_state"].apply is False
    assert doi.apply is False
    # Several sources are human_fetch and name a probe that is not implemented yet. That is safe
    # ONLY because survey() never probes a human_fetch source, so assert exactly that invariant:
    # every automated source's probe must exist, and flipping human_fetch off without writing the
    # probe fails here rather than as an unknown-probe ProbeError in a live run.
    from scripts.refresh.probes import _PROBES
    for s in srcs:
        if not s.human_fetch:
            assert s.probe in _PROBES, f"{s.id}: probe {s.probe!r} is not implemented"
    # a human-fetched source must carry a due date, or it ages by nothing
    for s in srcs:
        if s.human_fetch:
            assert s.due, f"{s.id} is human-fetched with no due date"
    # every target must exist
    for s in srcs:
        for t in s.targets:
            assert (REPO / t).exists(), f"{s.id} -> missing target {t}"
except Exception as e:  # ImportError, AssertionError, ValueError, ...
    print(f"FAIL: {type(e).__name__}: {e}")
    sys.exit(1)
print(f"PASS: {len(srcs)} sources")
