# Expense Classification Rules

These rules govern how every transaction in nanoclaw-finance is categorised.
They are applied in order — the first matching rule wins.
All amounts are in PKR.

---

## Categories

### 1. Food & Groceries
Applies to purchases at general stores, kiryana shops, supermarkets, and
online grocery services (e.g. Airlift, Grocerapp, Carrefour, Imtiaz).
Also covers bulk household food purchases.

Keywords: grocery, groceries, kiryana, supermarket, imtiaz, carrefour, metro,
hyperstar, store, mart, ration.

Does NOT include: restaurants, cafes, takeaway orders (those go to Dining Out).

### 2. Dining Out
Applies to restaurants, cafes, fast food outlets, food delivery apps,
and any sit-down or takeaway meal from a food business.

Keywords: restaurant, cafe, dhaba, dine, biryani, pizza, burger, kfc, mcdonalds,
pizza hut, subway, foodpanda, cheezious, karachi broast, chai dhaba.

Does NOT include: home grocery shopping (that goes to Food & Groceries).

### 3. Transport
Applies to fuel, ride-hailing, public transport, and vehicle running costs.

Keywords: petrol, fuel, diesel, cng, uber, careem, indriver, bus, wagon,
rickshaw, toll, parking, pump, shell, pso, total parco.

Does NOT include: vehicle purchase, major repairs (those go to Other).

### 4. Utilities
Applies to recurring home service bills: electricity, gas, water, internet,
and phone top-ups or postpaid bills.

Keywords: electricity, wapda, k-electric, sui gas, ssgc, sngpl, water, ptcl,
internet, wifi, jazz, telenor, zong, ufone, bill, utility.

### 5. Health & Medical
Applies to doctor consultations, pharmacy purchases, lab tests, hospital
fees, and health insurance premiums.

Keywords: pharmacy, medical, clinic, hospital, doctor, lab, test, dawakhana,
sehat, shifa, aga khan, oladoc, marham, medicine, tablet, injection.

### 6. Education
Applies to school or college fees, tuition, books, stationery, and
online course subscriptions.

Keywords: school, college, university, tuition, fee, books, stationery,
coursera, udemy, khan academy, academy.

### 7. Shopping & Apparel
Applies to clothing, shoes, accessories, and general retail shopping
(non-grocery).

Keywords: clothes, shirt, shoes, jeans, kurta, shalwar, fabric, daraz,
khaadi, gul ahmed, sapphire, alkaram, bata, stylo, j., breakout.

### 8. Entertainment & Subscriptions
Applies to cinema, streaming services, games, events, and hobby expenses.

Keywords: cinema, nueplex, cinestar, netflix, youtube premium, spotify,
game, ticket, event, concert, subscription.

### 9. Savings & Investments
Applies to transfers to savings accounts, investments, prize bonds,
mutual funds, and any intentional wealth-building movement of money.

Keywords: savings, investment, mutual fund, prize bond, deposit, meezan,
hbl saving, national savings, naya pakistan certificate.

### 10. Other
Catch-all for anything that does not match the above categories.
These entries must be reviewed manually before the weekly report is finalised.

---

## General Rules

1. **Currency check** — reject any row where the amount field is empty, zero,
   or non-numeric. Flag it for manual review rather than assigning a category.

2. **Case insensitivity** — keyword matching is case-insensitive.
   "PETROL", "Petrol", and "petrol" all match Transport.

3. **Partial matches count** — a description containing a keyword anywhere in
   the string is a match (e.g. "Shell petrol pump" matches "petrol").

4. **Conflict resolution** — if a description matches keywords from two
   categories, prefer the more specific one. If still ambiguous, assign Other
   and flag for review.

5. **Notes and memos files** (e.g. notes.txt) are informational only.
   They do not generate transactions; their content may be used to correct
   or annotate existing entries during manual review.

6. **Files without extension** (e.g. `datafile`) must be inspected and their
   format confirmed before any classification is attempted.

7. **Amount formatting** — all classified amounts must be stored and displayed
   as `PKR X,XXX.XX` (two decimal places, comma thousands separator).

8. **Raw data is read-only** — classification always operates on a copy in
   `data/organised/`. The original files in `data/raw/` are never modified.

---

## Review Triggers

The following conditions must pause automated classification and queue the
entry for human review:

- Amount exceeds PKR 50,000 in a single transaction.
- Description field is blank or contains only whitespace.
- Category assigned is Other.
- Date is missing, malformed, or in the future.
- Duplicate transaction detected (same date + amount + description).

## Category Priority Orders (highest wins on conflict)
1. Health & Medical
2. Education
3. Savings & Investments
4. Utilities
5. Dining Out
6. Food & Groceries
7. Transport
8. Shopping & Apparel
9. Entertainment & Subscriptions
10. Other
