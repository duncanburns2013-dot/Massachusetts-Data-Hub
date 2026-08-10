# Business mode — scope for review

**Status: proposal, nothing built.** Same discipline as `LAYER3-SCOPE.md`, which found a
$633M double-count before anything shipped.

## Shape

A mode toggle above the existing tabs. Six views, **one engine, one constants file**:

```
[ Household | Business ]
   Massachusetts · New Hampshire · Compare the two
```

Not a second dashboard. The MA and MA-vs-NH pages were merged into one on 2026-08-08
precisely because two copies of the tax engine could drift apart; a second file would
recreate that. A toggle swaps the input panel and the layer definitions and reuses
everything else.

## Why this is on-strategy

New Hampshire's pitch is aimed at **businesses**, not shoppers. The billboard truck sent
to Manhattan in Nov 2025 targeted NYC business owners directly. There is no clean
MA-vs-NH business comparison anywhere; this would be it.

---

## Rates — verified

| | Massachusetts | New Hampshire |
|---|---|---|
| Profits | **8.00%** corporate excise on MA-attributable income | **7.5%** BPT (RSA 77-A) |
| Net worth / property | **$2.60 per $1,000** of the greater of taxable MA tangible property or taxable net worth | — |
| Minimum | **$456** | — |
| Wages | — | **0.55%** BET on compensation paid (RSA 77-E) |
| Sales tax on inputs | 6.25% | none |

Sources: MA DOR corporate excise guide / Mass Taxpayers Foundation; NH DRA. The NH rates
and both property-rate tables are **already in `data/burden-constants.json`**.

## ⚠️ The BET credit — the thing most comparisons get wrong

BET credits are applied against BPT liability. A New Hampshire firm paying both
effectively pays **the greater of the two, not the sum.** NHFPI reports BET credits
equal to roughly 74% of BET liability being used against BPT.

Anyone who models NH as 7.5% + 0.55% overstates it. Getting this right is the single
strongest reason for a finance-literate reader to trust the rest of the page — and it is
already noted in the constants file under `NH.enterpriseTaxPool`.

---

## Still to source

| figure | where | note |
|---|---|---|
| MA PFML employer contribution | MA DFML, 2026 schedule | No NH equivalent — a real asymmetry, not an omission |
| Employer UI contributions | MA EOLWD; NH Employment Security | Needed for BOTH states or the comparison tilts |
| MA sales tax on business inputs | not separately reported | Would be a **modelled** share — a step down in evidence quality from everything else on the page |

## Collisions to check before building

1. **Business real estate vs the household property tables.** The 351 MA and 228 NH town
   figures are residential. Commercial rates differ, and MA municipalities may run a
   split rate. Do not reuse the residential tables for business property.
2. **Employer UI appears in both modes.** In Household it is a hidden cost passed into
   wages; in Business it is a direct cost. Same tax, two different treatments — correct,
   but it must be deliberate and labelled, not accidental.
3. **Sales tax on inputs vs Layer 1.** The household already pays sales tax directly.
   Only the business-paid share belongs in Business mode.

## Recommendation

Build the mode toggle and the **verified rates only** first — profits, net worth,
minimum, BET with the credit modelled properly, sales tax on inputs, and business
property. That is a defensible tool on its own.

Add PFML and employer UI in a second pass, once both states are sourced for the same
fiscal year. Leave the modelled input-tax share until last, and label it clearly as
modelled when it lands.
