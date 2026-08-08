# Layer 3 expansion — scope for review

**Status: proposal, nothing built.** Written for review before any figure goes into
`data/burden-constants.json`.

## The critique

> "You could *dramatically* plus up the business taxes section. So many other things in there."

Correct. Layer 3 currently contains two pools:

| pool | value | source |
|---|---|---|
| Federal corporate income tax | $452,089,303,420 | Treasury Final MTS, Sept 2025 |
| MA corporate & business excise | $4.662B | MA DOR FY2025 close |
| NH business taxes (BPT + BET) | $1,102.6M | NH DAS, June FY2025 accrual |

"Taxes businesses pay and pass on to households" is a much larger category than
corporate income tax.

---

## ⚠️ Collision found first — this one is load-bearing

**The existing $4.662B MA figure is already a combined number.** From the DOR FY2025
Annual Report, collections by type:

| type | FY2025 |
|---|---|
| Corporations | $4,036,624K |
| Insurance | $613,268K |
| Financial Institutions | $19,949K |
| **sum** | **$4,669,841K ≈ $4.67B** |

That reconciles to the $4.662B already in the model. So **insurance and financial
institution excises are already counted.** Adding them as new pools would double-count
roughly $633M — about 14% of the MA pool — and inflate the layer for every household.

This is exactly the failure the critique invites, so it goes at the top.

---

## Candidate additions, ranked

### 1. Employer unemployment insurance contributions — **best candidate**
- **Why it qualifies:** a tax on employers, levied on wages, not in any current layer.
- **Why it fits cleanly:** the base is compensation paid, so it behaves like NH's BET —
  the model already has a ~90%-to-labour slider for exactly this shape.
- **Not double-counted:** UI contributions go to a trust fund, not DOR tax collections,
  so they are absent from the $4.662B above.
- **Source needed:** MA EOLWD / UI Trust Fund annual contributions; NH Employment
  Security equivalent. Must be sourced for BOTH states or it tilts the comparison.

### 2. Sales tax on business inputs
- **Why it qualifies:** businesses pay 6.25% on much of what they buy and recover it in
  prices. Genuinely hidden.
- **The hard part:** not separately reported. Would need an estimated business share of
  the sales tax base — a modelled assumption, not a filed figure, which is a step down in
  evidence quality from everything else on the page.
- **Collision risk:** the household's own sales tax is already Layer 1. Only the
  *business-paid* share belongs here.

### 3. Business personal property tax
- **Why it qualifies:** equipment and machinery taxed locally, recovered in prices.
- **Collision risk: HIGH.** This is property tax. Layer 1 counts the household bill from
  the DLS average single-family figure, which is residential-only — so in principle no
  overlap. Needs confirming before use.

### 4. Public utility excise
- **Collision risk: HIGH.** Layer 4 already counts filed utility tariff charges. Any
  utility excise recovered through rates may already be inside those figures. Verify
  against the tariff before adding.

---

## What this needs before building

1. A sourced revenue figure per pool, **per state**, same fiscal year — asymmetry here
   rigs the cross-border comparison, which is the whole point of the page.
2. A defensible labour/capital split per pool. Wage-based taxes behave like the BET;
   input taxes are closer to pure price pass-through. Getting these wrong inflates the
   least-verifiable layer in a way a reader cannot audit.
3. A collision check against Layers 1 and 4 for each pool.

## Recommendation

Do **#1 only** in the first pass. It is the largest genuinely-missing pool, the incidence
is the best understood, it has no collision risk, and it exists in both states so the
comparison stays honest. Treat #2–#4 as a separate decision.

The pipeline is already built for this: each pool is a JSON entry with a source URL and a
verified date, and `update-burden-constants.py` refuses to publish any figure lacking
either.
