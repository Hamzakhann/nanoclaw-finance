# FILE INVENTORY — data/raw/

Generated: 2026-06-17

---

## ls -la

```
total 48
drwxr-xr-x  8 nisum  staff  256 Jun 17 16:38 .
drwxr-xr-x  4 nisum  staff  128 Jun 17 16:11 ..
-rw-r--r--  1 nisum  staff   10 Jun 17 16:38 Report.CSV
-rw-r--r--  1 nisum  staff   16 Jun 17 16:38 datafile
-rw-r--r--  1 nisum  staff   76 Jun 17 16:37 expenses_feb.CSV
-rw-r--r--  1 nisum  staff  109 Jun 17 16:37 expenses_jan.csv
-rw-r--r--  1 nisum  staff   77 Jun 17 16:37 notes.txt
-rw-r--r--  1 nisum  staff   17 Jun 17 16:37 receipt_march.pdf
```

---

## find

```
/Users/nisum/Desktop/nisum/llm-projects/nanoclaw-finance/data/raw/
/Users/nisum/Desktop/nisum/llm-projects/nanoclaw-finance/data/raw/Report.CSV
/Users/nisum/Desktop/nisum/llm-projects/nanoclaw-finance/data/raw/expenses_jan.csv
/Users/nisum/Desktop/nisum/llm-projects/nanoclaw-finance/data/raw/notes.txt
/Users/nisum/Desktop/nisum/llm-projects/nanoclaw-finance/data/raw/expenses_feb.CSV
/Users/nisum/Desktop/nisum/llm-projects/nanoclaw-finance/data/raw/receipt_march.pdf
/Users/nisum/Desktop/nisum/llm-projects/nanoclaw-finance/data/raw/datafile
```

---

## du -ah

```
4.0K    Report.CSV
4.0K    expenses_jan.csv
4.0K    notes.txt
4.0K    expenses_feb.CSV
4.0K    receipt_march.pdf
4.0K    datafile
 24K    data/raw/  (total)
```

---

## Summary

| # | Filename           | Extension | Size  |
|---|--------------------|-----------|-------|
| 1 | Report.CSV         | .CSV      | 10 B  |
| 2 | datafile           | (none)    | 16 B  |
| 3 | expenses_feb.CSV   | .CSV      | 76 B  |
| 4 | expenses_jan.csv   | .csv      | 109 B |
| 5 | notes.txt          | .txt      | 77 B  |
| 6 | receipt_march.pdf  | .pdf      | 17 B  |

**Total files: 6**

---

## Unique File Extensions

| Extension      | Count | Files                                    |
|----------------|-------|------------------------------------------|
| .csv / .CSV    | 3     | expenses_jan.csv, expenses_feb.CSV, Report.CSV |
| .txt           | 1     | notes.txt                                |
| .pdf           | 1     | receipt_march.pdf                        |
| (no extension) | 1     | datafile                                 |

**Distinct extension types: 4** (.csv/.CSV treated as same format, different case; (none) counted separately)

---

## Notes

- `.csv` and `.CSV` are the same format but differ in capitalisation — normalisation may be needed during ingestion.
- `datafile` has no extension; content type is unknown until inspected.
- All files are very small (10–109 bytes); likely stub/test data, not real transaction histories.
- No files were moved or modified during this survey.
