# Pocket Fitter: one-page write-up

*Since AI 2026 × Takomo Golf: "The Fitter in Your Pocket"*

## The idea

Most golfers buy irons online without a fitting, and Takomo's current tool is 12 questions plus a
fixed rule table. Pocket Fitter replaces the form with a short **chat interview** that collects
the same questionnaire. It then recommends a **buildable Takomo spec** (head, shaft, grip, length,
lie, stock or custom) and grounds the pick in **"golfers like you"**: what fitted the 50 most
similar of Takomo's 20,000 training golfers, found with MongoDB Atlas Vector Search.

```
chat interview ──► PlayerProfile ──► similar golfers (Atlas Vector Search) ──► decision engine ──► Takomo spec + evidence card
 (Gemini or scripted)   (Takomo's questions)    50 nearest of 20k, their reference fits    rules | gemini | jeff
```

## What the PoC proves

1. **Nearest-neighbour fitting beats today's rules on the same inputs.** On Takomo's dev split
   (3,000 golfers), scored with **Takomo's own scorer**, questionnaire answers only:

   | | Spec Agreement Score | Full spec exact | Flex | Shaft model | Grip | Lie |
   |---|---|---|---|---|---|---|
   | Takomo rules, questionnaire only (B1) | 77.1 | 13.7 % | 71.6 % | 61.6 % | 80.5 % | 41.3 % |
   | **Pocket Fitter, golfers like you** | **80.2** | **17.5 %** | **79.6 %** | **73.1 %** | **85.3 %** | 42.5 % |
   | *Takomo rules + phone/launch-monitor evidence (B2)* | *83.6* | *25.3 %* | *85.0 %* | *71.4 %* | *85.5 %* | *55.5 %* |

   The head pick ties with the rules (91.8 %). The gain comes from shaft flex, model and grip,
   where self-reported speed and carry are noisy and neighbours absorb that noise. B2 shows the
   bigger prize: real measurements, especially for lie.
2. **The whole loop runs end to end.** Chat, structured profile, vector search, pluggable decision
   engine, then a card with the Takomo product photo, price and link. Fittings are saved to MongoDB.
   Without Gemini or Mongo the app degrades to a scripted interview and an in-memory search.
3. **An LLM can sit in the loop without inventing products.** The Gemini engine can only return
   slugs from Takomo's catalog, and any spec Takomo can't build is rejected.

## How accuracy would be validated

- **Offline, now:** `scripts/eval_similar.py` reproduces the table above with Takomo's
  `takomo_fit.score` (exact-match credit per spec field, close-call rules, buildability check).
  Feature weights were tuned on dev, so the next run must use the held-out **test split** (scored
  by Takomo). We also want per-segment numbers (women, seniors, left-handers, close calls) so a
  gain in one group can't hide a loss in another.
- **Data caveat:** the training golfers and their "reference fits" are Takomo's **simulated**
  population (see `docs/SIMULATOR.md` in the pack). The PoC proves the method, not real-world
  accuracy.
- **Real-world:** run the fitter before an in-store TrackMan fitting at the event and on real
  customers. Compare our spec with the fitter's final build, and the expected carry and dispersion
  with the measured shots. After purchase, track returns, re-shafts and lie changes as ground
  truth. Feed confirmed fits back into the `golfers` collection so the neighbours become real
  golfers over time.
- **LLM engine:** score the Gemini (and Jeff) engines with the same scorer as `rules`, and ship one
  only if it beats `rules` on test.

## How trust was designed in

- **Show the evidence, not just the answer.** Every recommendation carries its "golfers like you"
  breakdown (head shares, shaft, flex, grip, length, lie, expected 7-iron carry) and plain reasons
  ("50 of the 50 most similar golfers were fitted into the Iron 101 MKII").
- **Honest confidence.** In the `rules` engine, confidence combines how much the neighbours agree
  with how complete the answers are, so a vague interview gets a visibly lower score. The Gemini
  engine is told to lower it when key answers are missing.
- **Only real, buildable products.** The catalog is Takomo's unmodified `takomo_products.json`.
  The interview LLM may not name clubs. Engine output is checked against head-shaft compatibility
  and the length, lie and grip options, and stock or custom is computed, not generated.
- **Deterministic safety net.** If any engine fails or returns something invalid, the `rules`
  engine answers. Tests and the no-key demo use the same path.
- **Humble about fit details.** Length and lie always come with "confirm with a static measurement
  or ball-line test", since lie is the weakest field without measurements.
- **Minimal data.** Fittings are stored under a random id with the answers and the recommendation,
  with no name or contact details. Secrets live in env or Secret Manager and are never committed.

## Next steps

1. **Add measurement evidence to the vectors:** phone height, wrist-to-floor and hand length, video
   swing speed and tempo, and ball-line or impact tests. B2's +6.5 points show the headroom, mostly
   in lie.
2. **Hybrid pick:** take Takomo's rule-based head, which is equal on head, and use neighbours for
   shaft, grip, length and lie. Show both heads when it is a close call.
3. **Validate on the test split and live** (as above), then tune `k` and the weights per segment.
4. **Seed Atlas and deploy:** run `python -m app.seed` against the cluster, add `MONGODB_URI` to
   Cloud Run, and top up Gemini credits.
5. **Jeff engine:** plug the open-source Jeff-1 decision model (Qwen3-4B LoRA, outputs
   probabilities) into `app/decision/jeff.py` to choose between the top candidate heads, as a
   calibrated, locally run alternative to Gemini.
6. **Close the loop:** "buy this spec" deep-links to the Takomo product page, and confirmed fits
   flow back as new reference golfers.

*Code: `backend/app/services/similar.py` (vector search), `backend/app/decision/` (engines),
`scripts/eval_similar.py` (evaluation). See the README for setup.*
