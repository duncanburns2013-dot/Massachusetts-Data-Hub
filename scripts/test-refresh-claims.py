"""Claim registry test. Prints and exits 0 on pass, 1 on fail. Stdlib only."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.refresh.claims import Claim, UnknownFigure, evaluate, load_claims
from scripts.refresh.register import load_sources


def raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    return False


try:
    # the worked example: this claim was live and inverted (2023 NAIC values)
    c = Claim(id="ma_auto_cheaper", page="healthcare-dashboard.html",
              text="MA auto is cheaper than the national average",
              figures=["ma_auto_expenditure", "us_auto_expenditure"],
              relation="ma_auto_expenditure < us_auto_expenditure")
    v = evaluate([c], {"ma_auto_expenditure": 1326.46, "us_auto_expenditure": 1281.61})[0]
    assert v.claim_id == "ma_auto_cheaper" and v.status == "broken"
    v = evaluate([c], {"ma_auto_expenditure": 1200.0, "us_auto_expenditure": 1281.61})[0]
    assert v.status == "holds"

    # every operator, both ways round
    for op, a, b, want in [("<", 1, 2, True), ("<", 2, 2, False), ("<=", 2, 2, True),
                           (">", 3, 2, True), (">", 2, 2, False), (">=", 2, 2, True),
                           ("==", 2, 2, True), ("==", 2, 3, False),
                           ("!=", 2, 3, True), ("!=", 2, 2, False)]:
        k = Claim(id="k", figures=["a", "b"], relation=f"a {op} b")
        got = evaluate([k], {"a": a, "b": b})[0].status
        assert got == ("holds" if want else "broken"), (op, a, b, got)
    # no spaces, and a numeric literal operand
    assert evaluate([Claim(id="k", figures=["a"], relation="a>100")], {"a": 105.8})[0].status == "holds"
    assert evaluate([Claim(id="k", figures=["a"], relation="a >= 1e2")], {"a": 99})[0].status == "broken"

    # no relation -> suspect when a figure it rests on moved
    c2 = Claim(id="x", figures=["bea_rpp_state"])
    assert evaluate([c2], {"bea_rpp_state": 105.8}, moved={"bea_rpp_state"})[0].status == "suspect"
    assert evaluate([c2], {"bea_rpp_state": 105.8}, moved=set())[0].status == "holds"
    assert evaluate([c2], {"bea_rpp_state": 105.8})[0].status == "holds"

    # a claim naming an unregistered figure fails loudly, with or without a relation
    assert raises(UnknownFigure, lambda: evaluate(
        [Claim(id="typo", figures=["census_acs1_ma_incom"])], figures={}))
    assert raises(UnknownFigure, lambda: evaluate(
        [Claim(id="typo", figures=["a", "bb"], relation="a < bb")], {"a": 1}))
    # an id only in the relation, not in figures, is still checked
    assert raises(UnknownFigure, lambda: evaluate(
        [Claim(id="typo", figures=["a"], relation="a < bb")], {"a": 1}))

    # known-but-valueless: exists in the system, no value handed in -> suspect, never holds
    known = {"ma_auto_expenditure", "us_auto_expenditure"}
    v = evaluate([c], {}, known=known)[0]
    assert v.status == "suspect"
    assert evaluate([c2], {}, known={"bea_rpp_state"})[0].status == "holds"
    # ...and a typo is still unknown even when a known set is supplied
    assert raises(UnknownFigure, lambda: evaluate([c], {}, known={"ma_auto_expenditure"}))

    # relations we cannot parse raise; they never pass
    for bad in ["", "a", "a <", "< b", "a < b < c", "a = b", "a <> b", "a and b",
                "__import__('os') < 1", "a.b < 1", "a < b; b", "a < (b)", "a < -b",
                "1 < 2 or a < b"]:
        k = Claim(id="k", figures=["a", "b"], relation=bad)
        assert raises(ValueError, lambda: evaluate([k], {"a": 1, "b": 2})), f"accepted {bad!r}"
    # non-numbers and NaN are refused, not compared
    for val in ("1", None, True, float("nan")):
        k = Claim(id="k", figures=["a"], relation="a < 5")
        assert raises(ValueError, lambda: evaluate([k], {"a": val})), f"accepted {val!r}"

    # order and count are preserved
    out = evaluate([c2, c], {"bea_rpp_state": 1, "ma_auto_expenditure": 2, "us_auto_expenditure": 1})
    assert [x.claim_id for x in out] == ["x", "ma_auto_cheaper"]

    # the shipped file loads, and every figure it names is resolvable
    claims = load_claims(REPO / "data" / "claims.json")
    ids = [x.id for x in claims]
    assert len(ids) == len(set(ids)), "duplicate claim id"
    assert "ma_auto_cheaper" in ids
    srcs = {s.id for s in load_sources(REPO / "data" / "sources.json")}
    # figures outside the source register are exactly the two NAIC auto ids, so a typo shows here
    naked = {f for x in claims for f in x.figures} - srcs
    assert naked == {"ma_auto_expenditure", "us_auto_expenditure"}, naked
    evaluate(claims, {}, known=srcs | naked)  # must not raise UnknownFigure
    for x in claims:
        assert (REPO / x.page).exists(), f"{x.id} -> missing page {x.page}"
        assert x.text.strip(), f"{x.id} has no text"
        page = (REPO / x.page).read_text(encoding="utf-8")
        assert x.anchor in page, f"{x.id}: anchor not found on {x.page}"
    # with the real 2023 figures the shipped inverted claim is broken
    shipped = {x.id: x for x in claims}["ma_auto_cheaper"]
    assert evaluate([shipped], {"ma_auto_expenditure": 1326.46,
                                "us_auto_expenditure": 1281.61})[0].status == "broken"
except Exception as e:  # ImportError, AssertionError, ValueError, ...
    print(f"FAIL: {type(e).__name__}: {e}")
    sys.exit(1)
print(f"PASS: {len(claims)} claims")
