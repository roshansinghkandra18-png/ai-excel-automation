# Latest Test Run — Daily Measurement Excel Filer

Date of this test: 2026-08-24
Tested on: throwaway test files in a `test_run` folder, using the CURRENT design (one Excel file per month, inside a Year subfolder). Your real files (Downloads master file, and your actual office folder) were never touched by any of this.

## Totals
- Tests run: 4
- Passed: 4
- Failed: 0

---

## Test 1: A normal day with 4 dictated patients (mix of clean and messy lines)

**What was fed in** (pretend dictated PDF text, standing in for a real PDF):
```
Date 1st September 2026
Patient Savita Aggarwal, doctor Self, code SC-3, size 44 inches, units 2, mobile 9876543210, amount 5000, Kakinada
Patient Ram Prasad, doctor Lal, code SC-19G, size 44 inches, units 2
Patient Confusing Entry With No Label At All Just Random Words
Patient Aarti Garg, doctor Sanjay Garg, code SC-1, size 40, units 2 pair, mobile 9899642701, FOC, replacement
```

**What was expected:**
- A brand-new file gets created at `records\2026\SEPTEMBER 2026.xlsx` (year folder made automatically)
- All 4 rows get added below the header, each dated 1 September 2026
- Savita's leftover word "Kakinada" (no label) lands in Miscellaneous, not lost or misplaced
- Aarti's leftover words "FOC" and "replacement" both land in Miscellaneous together
- The 3rd, rambling line still gets accepted since it technically has a name — a known limit, not a crash

**What was actually gotten:**
| Row | Date | Patient | Doctor | Code | Size | Units | Miscellaneous | Mobile | Amount |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 01-Sep-2026 | Savita Aggarwal | Self | SC-3 | 44 inches | 2 | Kakinada | 9876543210 | 5000 |
| 3 | 01-Sep-2026 | Ram Prasad | Lal | SC-19G | 44 inches | 2 | (blank) | (blank) | (blank) |
| 4 | 01-Sep-2026 | Confusing Entry With No Label At All Just Random Words | (blank) | (blank) | (blank) | (blank) | (blank) | (blank) | (blank) |
| 5 | 01-Sep-2026 | Aarti Garg | Sanjay Garg | SC-1 | 40 | 2 pair | FOC; replacement | 9899642701 | (blank) |

**Result: PASSED.** File created in the right place, all 4 rows landed with values in the correct columns.

**Worth noting (a real limit, not a bug):** Row 4 shows what happens when a name is dictated with zero other labeled fields — the whole sentence becomes the "name" since there's nothing to separate it. This is exactly the kind of case to bring back later if it keeps happening for real entries, per our agreed process (you show me the recurring mistake, I fix the rule, you get an updated version).

---

## Test 2: Second day's PDF adds to the SAME month file, doesn't make a duplicate

**What was fed in:** A second day's dictation, dated 2nd September 2026, with one new patient (Gaurav Mehta).

**What was expected:** The program finds "SEPTEMBER 2026.xlsx" already exists (from Test 1) and adds this new row below the existing 4, in that same file — no second file created for September.

**What was actually gotten:** Row 6 was added to the same `SEPTEMBER 2026.xlsx`, dated 02-Sep-2026, sitting right below the 1st's entries. Only one September file exists.

**Result: PASSED.**

---

## Test 3: A date the program can't understand — refuses to guess

**What was fed in:** `Date gibberish not a date`, followed by one otherwise-normal patient line.

**What was expected:** Since every row needs a real date, and this one can't be understood, the program should stop and flag it rather than guess a date or write anything.

**What was actually gotten:**
```
Flagged: "Date: gibberish not a date" -> Found a date label but could not understand the date text
```
Nothing was written to any file.

**Result: PASSED.** No silent guessing on something as important as the date.

---

## Test 4: Refuses to write into a file with unexpected columns

**What was fed in:** A pretend scenario where "OCTOBER 2026.xlsx" already exists but with completely different, unexpected columns (as if someone had manually created or edited it differently) — then a normal dictated entry for that same month.

**What was expected:** The program should refuse to add rows into a file whose columns don't match what it expects, rather than risk scrambling the data.

**What was actually gotten:**
```
CORRECTLY BLOCKED: 'OCTOBER 2026.xlsx' already exists but its columns don't match
what this program expects, so nothing was written (to avoid mixing up your data).
```

**Result: PASSED.**

---

---

## Test 5: A REAL dictated PDF (Date.pdf), not sample text

**What was fed in:** Your actual PDF, dictated for real via Wispr Flow, with 4 patients (Akshita, Ruhani, Dharamraj, Savina). This revealed the real format is different from what was assumed earlier — one field per line ("Label: value"), blank line between patients, and labels like "Model Number" and "Number of Units" instead of "code"/"units". **Fixed the parser to match your real wording.**

**What was expected:** All 4 patients correctly split into columns, with Location/Office/FOC (no matching column) landing in Miscellaneous, and the date "1st July 2026" understood correctly.

**What was actually gotten:** All 4 entries parsed correctly, 0 flagged. File created at `records\2026\JULY 2026.xlsx`.

**Result: PASSED**, after fixing the parser to match your real dictation style.

**Two things to flag back to you (not fixed automatically, since I don't guess):**
- None of the 4 entries had a SIZE — your PDF never said "Size:" for anyone. Need to confirm: was that skipped for this test, or does size need a different word when you dictate it?
- Dharamraj's "Number of Units" was dictated as 40 — unusually high, worth double-checking that's really what you meant.

---

## Test 6: Formatting fixes (after your feedback on Test 5's output)

**What was fed in:** Same real PDF as Test 5, re-run after fixing the Excel styling.

**What was expected (your reported problems):**
- Columns too narrow, date and other columns not fully visible
- "Number of Units" column not consistently aligned
- "Amount" column inconsistent — 5,000 and 3,000 right-aligned but 10,000 left-aligned (root cause: "10,000" was stored as TEXT because of the comma, while 5000/3000 were stored as real numbers)
- No proper borders or header color-coding

**What was actually gotten (verified by reading the saved file back):**
- Column widths now auto-size to fit the longest value in each column (e.g. Date=14, Miscellaneous=24, Doctor=20)
- "10,000" is now stored as the real number 10000 (displayed with a comma via formatting), matching 5000 and 3000 — all three are now the same data type
- Units and Amount columns: every row confirmed center-aligned (your choice)
- Every cell confirmed to have a thin border
- Header row confirmed: dark blue background, bold white text

**Result: PASSED.**

---

## Test 7: Model number hyphens, Miscellaneous label stripping, SIZE removed

**What was fed in:** Same real PDF, after three more of your fixes: (1) model numbers like "SC1" should read "SC-1", (2) Miscellaneous should show just "Chandigarh" not "Location: Chandigarh", (3) SIZE column removed entirely since you don't want it. Also confirmed: Dharamraj's 40 units was intentional, not a mistake.

**What was expected:** CODE column hyphenated correctly for all 4 patients; Miscellaneous shows bare location/notes with no label word; no SIZE column anywhere.

**What was actually gotten:**
| Patient | Code | Miscellaneous |
|---|---|---|
| Akshita | SC-1 | Chandigarh |
| Ruhani | SC-66 | Bangalore |
| Dharamraj | SC-12 | Office |
| Savina | ST-66 | FOC |

**Result: PASSED.** Saved to a fresh test file since the previous one was still open in Excel: `test_run2\records\2026\JULY 2026.xlsx`.

---

## Test 8: Packaged into the double-click .exe

**What was done:** Built the program into a standalone `Daily_Measurement_Excel_Filer.exe` (no Python needed to run it) and launched it to confirm it opens without crashing.

**What was expected:** The program window opens normally, same as running the script directly.

**What was actually gotten:** Exe launched successfully, ran in the background, closed cleanly. File is ~23 MB, sitting in `Office Package\Daily_Measurement_Excel_Filer.exe`, alongside a `HOW TO USE.txt` instructions file for office staff (covers first-time setup, daily use, and exactly how to dictate a PDF so it parses correctly).

**Result: PASSED (launch only).** This only confirms the exe *opens* without error — it has NOT yet been clicked through end-to-end (choosing a folder, choosing a PDF, checking the Excel result) by a human. That's the one thing still needed before this is truly "office ready."

**Result: user clicked through the whole flow themselves and confirmed it worked.**

---

## Test 9: Mobile number field blanked when office says "not known" / "not there"

**What was fed in:** Office feedback — when a mobile number isn't available, people say things like "not known" or "not there" instead of leaving it blank. Three test patients: one with "Mobile Number: not known", one with "Mobile Number: not there", one with a real number.

**What was expected:** Any Mobile Number value with no digits in it at all should end up blank in Excel, not store the words "not known"/"not there" as if they were a phone number. Real numbers should be unaffected.

**What was actually gotten:**
```
Test One  -> mobile: '' (was "not known")
Test Two  -> mobile: '' (was "not there")
Test Three -> mobile: '9876543210' (unaffected)
```

**Result: PASSED.** Rebuilt and reinstalled the .exe in Office Package with this fix; confirmed it still launches correctly.

---

## Test 10: The three office bugs (locked file, stray colon, green triangles)

**What was fed in:** Your three real office PDFs (`Pdf testing 1`, `pdf testing 2`, `pdf testing 3`), dated 1st, 2nd and 3rd April 2026.

**What was expected:**
- All three days land in one `APRIL 2026.xlsx`, appended one below the other
- Units read as plain `2`, not `:2` — the 2nd and 3rd both wrote it as `number of units :2` with a space before the colon
- If the file is open in Excel, a plain-English message instead of `Errno 13 Permission denied`
- Green "number stored as text" marks hidden on the Mobile column

**What was actually gotten:**
| Row | Date | Units | Stored as |
|---|---|---|---|
| 2 | 01-Apr-2026 | (blank) | — (that PDF has no units line at all) |
| 3 | 02-Apr-2026 | 2 | real number |
| 4 | 03-Apr-2026 | 2 | real number |

Locked-file message, confirmed by deliberately locking the file:
```
'APRIL 2026.xlsx' is currently open in Excel, so it could not be added to.
Please close that file in Excel, then click the green button again.
Nothing has been lost - just close it and try once more.
```
The "ignore this warning" instruction was confirmed present inside the saved file, covering the Mobile column.

**Result: PASSED, all three.**

**Note:** your 1st April PDF genuinely has no units line, so that row's units cell is empty. That's the PDF, not the program.

---

## Test 11: Visual redesign — still works after the rebuild

**What was fed in:** The original `Date.pdf` (4 patients), run through the fully redesigned interface, to confirm the new look didn't break the actual work.

**What was expected:** Identical Excel output to before the redesign — same 4 rows, same values, same columns.

**What was actually gotten:** Identical. 4 rows, `SC-1 / SC-66 / SC-12 / ST-66`, amounts 5000 / 3000 / 10000, Miscellaneous showing bare `Chandigarh` / `Bangalore` / `Office` / `FOC`. On screen the tiles correctly read **4 rows added · 0 needs checking · JUL 2026**.

**Result: PASSED.** The redesign is cosmetic only — the reading and filing behaviour is unchanged.

## What's NOT tested yet (needs you)
- The redesigned .exe hasn't been clicked through by a human yet — it launches correctly and the custom icon shows in the taskbar, but you should run one real PDF through it
- The mobile-number "not known" fix hasn't met a real office PDF yet — worth watching the next one that comes in









