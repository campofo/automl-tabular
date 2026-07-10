# Presenting at GSA 2026 — Speaker Guide

**Talk:** Comparative Evaluation of AutoML Frameworks for Tabular Data in
Resource-Constrained Environments — Implications for Data Science Practice in Ghana
**Slot:** 15–20 minutes + Q&A · **Venue:** Tamale Technical University, 25–29 August 2026
**Deck:** `slides/automl_presentation.tex` (Beamer; build with `pdflatex`, run twice)

---

## 1. Before the conference

- [ ] Re-run `notebooks/analysis.ipynb` after the full-budget campaign so
      `figures/*.png` hold **final** results, then rebuild the PDF
- [ ] Replace every slide marked **[UPDATE]** with final numbers; delete the
      "[UPDATE]" tags
- [ ] Fill the recommendation matrix — it is the slide people photograph
- [ ] Compile twice: `pdflatex automl_presentation.tex && pdflatex automl_presentation.tex`
- [ ] Export a PDF copy to a USB stick **and** email it to yourself; assume
      the venue machine has no LaTeX and possibly no internet
- [ ] Print the recommendation matrix as a one-page handout (~30 copies)
- [ ] Rehearse aloud 3×; target 16 minutes so questions never feel rushed
- [ ] Registration, travel Accra→Tamale (VIP/STC), accommodation booked
      (check TaTU dorm availability); conference contacts: conference@ghanasa.org,
      0243912246 / 0208012789

## 2. Timing plan (16 minutes)

| Slides | Section | Time | Purpose |
|---|---|---|---|
| 1–2 | Title + the question | 2 min | Hook: "given what we have" |
| 3–5 | Frameworks, tiers, datasets | 3 min | Design credibility |
| 6–7 | Metrics + reproducibility | 2 min | Why completion rate is novel |
| 8–10 | Three results figures | 5 min | The evidence — slow down here |
| 11–12 | Pilot findings + recommendation matrix | 2.5 min | The deliverable |
| 13–15 | Policy, limitations, summary | 1.5 min | Land the "so what" |

**Golden rule:** if running long, cut slide 6 (metrics) and slide 14
(limitations) verbally — never cut the figures or the matrix.

## 3. Per-slide talking points

- **Slide 2 (the question):** open with a story — a district statistician
  with one 4 GB laptop asked which tool to install. The literature answers
  for AWS, not for her. That gap is this study.
- **Slide 4 (tiers):** stress *enforced*, not simulated: containers are
  hard-capped; a framework that overflows 4 GB dies exactly as it would on
  the real laptop. This is what distinguishes the study from prior work.
- **Slide 5 (datasets):** one sentence each on why the domains map to
  Ghanaian institutions (fraud → banking supervision; housing → urban
  planning; wine → agricultural grading).
- **Slides 8–10 (figures):** narrate one concrete point per figure, e.g.
  "on the constrained tier, moving from X to Y buys 3 F1 points for 5× the
  memory — that's the trade-off a procurement officer needs to see."
- **Slide 11 (pilot findings):** the budget-discipline finding is the most
  conversation-starting: some tools treat a time budget as a promise, others
  as a suggestion. On shared institutional machines that difference decides
  usability. (FLAML honoured every budget to the second; PyCaret overran
  120 s budgets ~7× and once had to be killed externally.)
- **Slide 12 (matrix):** say explicitly: "photograph this slide — it is the
  answer to the question in the title."

## 4. Anticipated questions (with answer sketches)

1. **"Why not test on actual GSS/GHS hardware?"** — Docker caps reproduce the
   binding constraints (RAM/CPU/time) exactly, and reproducibly; on-site
   replication with partner agencies is named future work.
2. **"Aren't public datasets unrepresentative of Ghanaian data?"** — They span
   the task *types* (imbalanced fraud, mixed-type tabular, small-n
   regression). A Ghana-specific suite is future work; the pipeline accepts
   any CSV.
3. **"Deep learning / LLMs instead of AutoML?"** — Out of scope and typically
   dominated by gradient boosting on tabular data at these scales; cite the
   AutoML benchmark literature.
4. **"Why these five frameworks?"** — Open-source, actively maintained,
   pip-installable, cover the main algorithmic families (CASH optimisation,
   ensembling, cost-frugal search).
5. **"How sensitive are results to the time budgets?"** — Directly addressed
   by the three tiers; degradation curves show each framework's sensitivity.
6. **"Can we run this ourselves?"** — Yes: repo is public, one command per
   stage, datasets fetch automatically with checksums. Offer to help after
   the session.
7. **"What about inference (deployment), not just training?"** — Honest
   answer: training-focused; inference cost noted as future work.

## 5. Delivery notes

- Audience mixes statisticians, ML practitioners, and policy people —
  define AutoML in one sentence early ("software that automates model
  selection and tuning"), then never re-explain.
- Numbers land better as comparisons than absolutes ("half the memory,
  same F1" beats "1 153 MB").
- If a demo is requested: don't live-demo Docker on venue Wi-Fi; show the
  logs.csv and a figure instead.
- Close Q&A by pointing to the repo URL and your emails (final slide stays up).

## 6. Materials checklist (day of talk)

- [ ] Laptop + charger + HDMI/VGA adapter
- [ ] PDF on laptop, USB stick, and email
- [ ] Printed recommendation-matrix handouts
- [ ] Printed speaker notes (this file, sections 2–4)
- [ ] Business cards / contact slips with the repo URL
