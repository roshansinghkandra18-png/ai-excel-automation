# Excel Measurement Automation: Brainstorm / Discovery Notes
Date: 2026-08-24 · Goal: Design and build an automation that takes a daily PDF of medical garment measurements and files each entry into the correct columns/rows of the user's fixed Excel register, replacing hours of manual daily typing.

## Summary / key decisions
- User currently: writes measurements by hand in a paper register (very messy handwriting), then manually retypes everything into Excel — takes hours daily.
- Tested: sent 2 photos of the actual handwritten register pages. Assistant honestly assessed readability: names/dates/headers readable, but dense measurement number grids were NOT reliably readable (ambiguous digits, one fully illegible rotated block). Decision: **do not build handwriting OCR off photos** — too risky for medical records.
- Confirmed direction instead: user will type/dictate entries (likely via Wispr Flow voice-to-text) into a PDF themselves, in their own words/order ("random order"), then hand that PDF to the automation. Assistant reads the PDF's typed text (reliable, since it's digital text not handwriting) and places each measurement into the correct pre-existing columns of the fixed Excel sheet.
- Trigger model confirmed by user: chat-driven — user drops a PDF in and tells the assistant (in Claude Code chat) to process it. Not a fully automatic folder-watcher, not a standalone double-click script (at least not yet).
- Not yet resolved: exact Excel column structure, row-matching key (name/code/date), dictation format for the PDF, whether user will share real Excel file for design purposes.

## Q&A log

### Q0 — PDF source type (asked before this grill-me session)
- Asked: What kind of PDF is your daily register in?
- Captured: User will type/dictate into the PDF themselves (using Wispr Flow to speed up typing from the handwritten register). Not a scan of handwriting.
- Flags: none — resolved.

### Q0b — Trigger method (asked before this grill-me session)
- Asked: How do you want to trigger this each day?
- Captured: "buddy i will just put a pdf and you will put the information into excel columns" — confirms chat-triggered, on-demand processing per PDF drop.
- Flags: none — resolved (this is the trigger model going forward).

### Q1 — Excel file structure
- Asked: share the real Excel file so assistant can inspect actual columns.
- Captured: File found at C:\Users\rosha\Downloads\DAILY PATIENT MAY 2016 ONWARD.xlsx (also a duplicate copy "(1)" in same folder). One sheet per calendar month from MAY 2016 through JULY 2025 (~120 sheets), column count has varied over the years (7 to 15 cols). Inspected latest sheet "JULY 2025": columns are DATE | PATIENT NAME | DOCTOR | CODE (e.g. SC-3) | NO. OF UNIT | (blank/city) | MOBILE NO. | AMOUNT. Only the first row of each day has the date; subsequent rows for that day have blank date cells (date fills down implicitly).
- **MISMATCH FOUND**: this sheet does NOT contain the detailed body-measurement numbers (the Lt/Rt number grids seen filling most of the handwritten register page). It's a simpler summary/order log (who, doctor, code, units, contact, amount) — not a measurement chart.
- Flags: Is this summary Excel actually the target, or is there a SEPARATE file/sheet where detailed measurements (the Lt/Rt number grids) get recorded? -> user, critical, blocks design of matching logic.
- **RESOLVED**: Confirmed — this summary log IS the correct target file. Detailed Lt/Rt measurement numbers do NOT need to go into Excel at all; they stay on paper in the register only. Excel only needs the summary/order info.

### Q2 — Desired column list (redesign)
- Asked: (follow-up after confirming this is the right file) what columns are actually wanted.
- Captured: User wants these columns going forward:
  1. DATE
  2. PATIENT NAME
  3. DOCTOR
  4. CODE — the product's model number, e.g. "SC-2", "SC-3", "SC-15" (this is what the old sheet's unlabeled 4th column already held)
  5. SIZE — currently jammed together with unit count in the old "NO. OF UNIT" column (e.g. old cell said `44"-2` meaning size 44" + 2 units); user wants SIZE split into its own column
  6. NO. OF UNITS — split out as its own column (just the count, e.g. `2`)
  7. MISCELLANEOUS — replaces the old vague blank/city column; covers: city, FOC (free of charge), replacement, or "on hold" (meaning: customer took measurement but didn't get the garment made yet)
  8. MOBILE NO.
  9. AMOUNT
- Flags: none yet — need to confirm this full list back to user as final before building; also still need to confirm exact wording/values expected inside MISCELLANEOUS (free text vs fixed set of tags) and SIZE format.

### Q3 — Miscellaneous, date fill-down, size format
- Asked: three quick format questions (Misc free text vs fixed tags; date on every row vs old blank-below style; size free text vs numeric).
- Captured:
  - MISCELLANEOUS = free text, and specifically a **catch-all**: anything in the dictated entry that doesn't map to the other 8 named fields (Date, Name, Doctor, Code, Size, Units, Mobile, Amount) automatically goes here. User will clearly label fields when dictating (e.g. say "doctor" before the doctor's name) so the other fields are easy to identify; whatever's left over (city, FOC, replacement, hold, etc.) falls into Misc.
  - DATE: put the date on every row (not the old style of blank-below-first-row). User confirmed the recommended option.
  - SIZE: free text, whatever is dictated, no forced numeric conversion. User confirmed the recommended option.
- Flags: none — resolved.

### Q4 — Append-only vs edit-existing, and monthly sheet behavior
- Asked: does every PDF add brand-new rows, or sometimes correct existing ones? Where does new data get written relative to the existing ~120 monthly sheets?
- Captured: **Always append-only.** Confirmed workflow: e.g. 1 Sept PDF -> converted, added to that month's sheet. 2 Sept PDF -> appended directly below 1 Sept's rows in the SAME month's sheet. When a new calendar month starts, automation creates a NEW sheet/tab for that month (matching the existing ~120-sheet-one-per-month pattern already in the workbook). Automation never edits/overwrites rows already in Excel — pure addition.
- Flags: none — resolved. This also fully answers the earlier "row-matching key" question — there is no matching needed at all, since nothing is ever looked up or overwritten, only appended.

### Q5 — File safety and dictation labeling style
- Asked: edit live file only, or keep a safe copy too? Will dictation include field labels?
- Captured:
  - File safety: **BOTH** — user wants the live Downloads file AND a separate backup copy updated to the latest data every run ("two records both updated to latest"). Not "copy first, promote later" — both get written same run, so this is a mirrored dual-write, not a staged review step.
  - Dictation style: user will say a **label before fields that need one** (e.g. "doctor Self", "code SC-3") — confirmed the recommended labeled approach. Reduces ambiguity for parsing.
- Flags: none — resolved.

### Q6 — Dictation template confirmed
- Asked: proposed template — say date once at top of day's dictation, then one labeled line per patient (e.g. "Patient Savita Aggarwal, doctor Self, code SC-3, size 44 inches, units 2, mobile 9876543210, amount 5000, Kakinada"), unlabeled trailing words fall into Miscellaneous. Confirmed date is said once but still gets written into EVERY row in Excel (assistant copies it down automatically) — clarified this doesn't conflict with the earlier "date on every row" decision (Q3), it's just input-vs-output.
- Captured: User confirmed this works exactly as proposed. **Dictation template is locked in.**
- Flags: none — resolved.

## Summary / key decisions (updated)
**FINAL DESIGN LOCKED IN:**
- Target file: C:\Users\rosha\Downloads\DAILY PATIENT MAY 2016 ONWARD.xlsx — one sheet per calendar month (~120 existing sheets, MAY 2016 to JULY 2025).
- New columns going forward: DATE | PATIENT NAME | DOCTOR | CODE | SIZE | NO. OF UNITS | MISCELLANEOUS | MOBILE NO. | AMOUNT (date filled on every row).
- Source of daily data: user dictates via Wispr Flow into a PDF, date said once at top, then one labeled line per patient (labels for doctor/code/size/units/mobile/amount; unlabeled leftover words -> Miscellaneous).
- Workflow: append-only. Each day's PDF adds new rows below existing ones in that month's sheet. New calendar month -> new sheet auto-created. Automation never edits/overwrites existing rows.
- Trigger: chat-driven, on demand — user drops a PDF and tells the assistant in Claude Code chat to process it (not a folder-watcher or standalone script, at least for v1).
- Safety: BOTH the live Downloads file AND a separate backup copy get updated to the latest data on every run (mirrored dual-write, not staged).
- No handwriting OCR — confirmed unreliable via live photo test on 2026-08-24, abandoned in favor of user's own typed/dictated PDF.

### Q7 — Backup location and ambiguous-data handling
- Asked: where should backup copy live? What should happen when a PDF entry is ambiguous/unclear?
- Captured:
  - Backup location: **separate backups folder** (inside this project folder, e.g. "backups"), physically separate from the live Downloads file, so a problem with one location can't take out both.
  - Ambiguous data handling: **flag for user review, never silently guess.** Everything clear gets processed normally; anything unclear gets shown to the user separately for a decision before it's placed anywhere. This matches the user's global CLAUDE.md principle "where automation runs out, put AI there... but flag it, don't default silently."
- Flags: none — resolved.

### Q8 — CRITICAL: handoff requirement changes architecture
- Asked (user-raised, not assistant-anticipated): "i have to give this once its made to someone then dont have claude how will they access it?"
- Captured: User needs to hand this tool off to someone who does NOT have a Claude account/Claude Code. This rules out the original plan of "Claude parses the PDF in chat each time."
- Resolution: since dictation is labeled/structured (per Q6 template), the parsing is mechanical, not genuinely AI-judgment-dependent for the normal case. **Decision: build a standalone plain program (no AI dependency) that reads the labeled PDF text and fills Excel using fixed rules.** Genuinely unclear/unparseable entries get listed separately for a human to fix by hand (not auto-guessed, not AI-called) — consistent with the earlier "flag, don't guess" decision (Q7). This makes the tool free, dependency-free (no API key, no subscription), and usable by literally anyone the file gets handed to.
- Flags: packaging format (does the recipient have Python installed, or does this need to be a double-click .exe with no setup?) -> needs one more question before build.

### Q9 — Packaging format and hardware constraint
- Asked: does the recipient know Python, or does this need to be a no-setup double-click file?
- Captured: **Standalone double-click .exe, no install needed.** Additional critical context (user volunteered mid-turn): this is for the user's OFFICE — it will run on coworkers' PCs, and those PCs are **8-9 years old**. Needs to be lightweight/simple to run, not resource-heavy. Implication for build: use a minimal, lightweight interface (e.g. built-in Tkinter, not a heavy framework) and keep the packaged program as simple/small as practical so it runs fine on old low-spec office machines.
- Flags: none — resolved, but this constraint should guide implementation choices (avoid heavy GUI frameworks, avoid unnecessary dependencies bundled into the .exe).

### Q10 — Ongoing maintenance process for flagged/unparseable entries
- Asked: (user-raised) what happens long-term with the things that get flagged instead of guessed?
- Captured: this is an ongoing feedback loop, not a one-time build. Process going forward: when the program repeatedly flags the same kind of entry as unparseable/ambiguous, the user will bring those recurring mistake patterns back to Claude (in a future chat session); Claude fixes the underlying parsing rules in the program and hands the user back an updated version of the .exe. So the program itself doesn't self-learn or call AI at runtime — the "learning" happens via the user periodically bringing real failure examples back to a human-in-the-loop (Claude) session, who patches the rules.
- Flags: none — resolved. Worth remembering for future sessions: this project will need periodic "here are the recurring flagged mistakes, please fix" follow-up sessions after initial build. -> [[project]] memory candidate once build is done and this pattern is proven out.

### Q11 — CORRECTION: separate file per month, not tabs in the old master workbook
- Asked (user-raised mid-build, after v1 was already built and tested against "one workbook, tab per month" like the old master file): should new data go into a NEW TAB in the old 10-year master file (as originally assumed in Q1/Q4), or into a completely separate, brand-new .xlsx FILE per month?
- Captured: **CORRECTION — separate file per month.** Old file `DAILY PATIENT MAY 2016 ONWARD.xlsx` stays exactly as-is, untouched, as historical archive. Going forward, automation creates one brand-new standalone Excel file per calendar month (e.g. "SEPTEMBER 2026.xlsx"), not a new tab inside the old file. By year end there will be 12 separate monthly files. Saved in the SAME folder as the old master file (Downloads), for now.
- This changes: `excel_writer.py` needs rework from "one workbook, find-or-create month SHEET" to "one workbook FILE per month, in a configured records folder." `config.py` needs to store a records FOLDER instead of a single excel file path.
- Flags: none — resolved, but requires reworking already-built code (excel_writer.py, config.py, main.py) and re-testing.

### Q12 — Real PDF test revealed the true dictation format (differs from Q6's guessed template)
- Captured: user's actual Wispr Flow PDF ("Date.pdf") used one field per line ("Label: value"), blank line between patients — NOT the single-line comma-separated format guessed in Q6. Real labels: "Name", "Doctor", "Model Number" (not "Code"), "Number of Units" (not "Units"), "Mobile Number" (not "Mobile"), "Amount". Parser rewritten to match reality and retested successfully — 4/4 real entries parsed correctly, 0 flagged.
- Follow-up fixes from user feedback on the real output: (1) CODE values now auto-hyphenated between letters and digits, e.g. "SC1" -> "SC-1"; (2) Miscellaneous strips any unrecognized "Label:" prefix and keeps just the value, e.g. "Location: Chandigarh" -> "Chandigarh"; (3) **SIZE column dropped entirely** — user doesn't want it; (4) confirmed Dharamraj's "40" units was intentional, not a parsing mistake.
- Also added: Excel styling — colored header row (dark blue fill, bold white text), thin borders on every cell, auto-sized columns based on content, consistent per-column alignment (center for Date/Code/Units/Mobile/Amount, left for Name/Doctor/Miscellaneous). Fixed root cause of inconsistent Amount alignment: "10,000" was being stored as text (comma broke int/float parsing) while "5000"/"3000" were real numbers — now all amounts strip commas before numeric conversion, then redisplay with a comma via Excel number format.

### Q13 — Packaged and shipped
- Built with PyInstaller: `pyinstaller --onefile --windowed --name "Daily_Measurement_Excel_Filer" main.py`. Confirmed it launches without crashing.
- Delivered as `Office Package\Daily_Measurement_Excel_Filer.exe` + `Office Package\HOW TO USE.txt` (plain-English setup/daily-use/dictation-format guide for non-technical office staff).
- User personally clicked through the full flow on their own machine (first-run folder picker tripped on trying to select a file instead of a folder — walked them through creating/selecting a folder instead) and confirmed: **"its working thankyou ill give it to my office."**
- Advised: send the whole Office Package folder (not just the exe) zipped, and each office PC needs its own one-time "Choose Folder for Excel Files" setup step since the folder choice is stored locally per machine (in a `settings.json` next to the exe), not shared.

### Q14 — Second round: real office bugs, structure change, full redesign (2026-08-27)
User ran the v1 .exe on an office PC and came back with real findings. All fixed and verified:
- **Locked file**: adding a PDF while the Excel file was open in Excel showed `Errno 13 Permission denied`. Replaced with a plain-English "close it in Excel and try again" message.
- **Stray colon**: office wrote `number of units :2` (space before colon), which stored `:2` as text instead of the number 2 — silently breaking the ability to total that column. Parser now strips leftover punctuation between any label and its value.
- **Green triangles** on Mobile column: Excel's "number stored as text" false alarm. Mobiles must stay text (spaces, leading zeros), so the "ignore this" instruction is now injected into the saved file. openpyxl can't do this, so it's done by editing the saved .xlsx afterwards.
- **CORRECTION to Q11**: user's office wants everything in ONE file again, with a tab per month (like their old master file) — not one file per month. Rebuilt around a single `DAILY PATIENT RECORD.xlsx`; tabs auto-created and kept in date order, so a back-dated PDF slots into the right position.
- **Full visual redesign** to the "Console" layout (dark side rail: Today / Activity / Settings; rounded cards; drawn icons; themed pop-ups). User rejected the earlier clinical-teal design as "not at all visually appealing". Harsh blue text selection replaced with a soft tint.
- **Windows file dialog replaced**: in-app "Recent PDFs" list (scans Downloads/Desktop/Documents) plus drag & drop via tkinterdnd2 (bundled into the .exe, so office PCs install nothing). "Browse…" kept as fallback.
- Global CLAUDE.md updated: all future automations/agents must be visually designed, never plain default UI (they go on the user's CV and in front of clients).

### Q15 — Pre-handover hardening (2026-08-27)
User asked what to test before giving it to their first client. Two genuine design gaps were surfaced proactively and then closed:
- **Duplicate protection**: the same PDF added twice created duplicate rows with no warning — a real risk for billing/patient records. Now PDFs are identified by their **contents** (so a renamed copy is still caught), with a warning naming when it was last filed and where, and an explicit "Add it again anyway" override.
- **Two people at once**: two PCs sharing a folder could silently wipe each other's entries. The file is now re-checked immediately before saving; if it changed underneath, the save is refused rather than overwriting someone's work.

### Q16 — Automated test suite (2026-08-27)
User asked about an external QA skills pack (qa-skills); advised against it — it targets web/API testing, not a Windows desktop app. Built a project-specific suite instead: `tests/run_tests.py` + `tests/pdf_maker.py`, run via `RUN TESTS.bat`. **28 tests, all passing.** It generates its own awkward PDFs (no dependencies), works in a throwaway sandbox, and overwrites `Test Results/latest_test_run.md` with a full plain-English report.
- The suite immediately earned its keep: it exposed that the parser relied entirely on blank lines between patients, so a PDF exporter that drops them would merge everyone into one record and silently lose the rest. Parser hardened so a new `Name:` line also starts a new patient.
- One test failed on first run and it was **the test that was wrong, not the code** (it demanded an empty row stay empty forever). Fixed the test, not the program — recorded here deliberately.
- Global CLAUDE.md updated with the universal "always test these" list distilled from what actually went wrong here.

## Open flags (pending input)
- **Nobody has clicked through the final .exe by hand.** It launches, the icon shows, drag-drop is bundled and verified present — but Windows would not let the automation bring its window in front of VS Code to drive it. Roshan must run one real PDF through it, especially the drag & drop.
- The mobile "not known" fix has not yet met a real office PDF.
- Pre-handover checklist for the office PCs (SmartScreen warning, antivirus, non-technical person doing setup unaided, shared network drive) — still to be done on actual office hardware.
- Strongly recommended before handover: run the tool **in parallel** with manual entry for 3-5 real days and compare.
- Standing process (per Q10): recurring flagged entries come back to a Claude session -> parser rules fixed -> new test added -> updated .exe.

## Final project layout
- `app/` — source: `main.py` (UI), `parser.py` (reads the PDF text), `excel_writer.py`, `pdf_reader.py`, `pdf_picker.py`, `history.py` (duplicate memory), `dialogs.py` (themed pop-ups), `theme.py`, `config.py`, `make_icon.py`
- `tests/` — `run_tests.py`, `pdf_maker.py`
- `RUN TESTS.bat` — double-click to run all 28 tests
- `Test Results/latest_test_run.md` — overwritten every run, always the current picture
- `Office Package/` — what the office gets: `Daily_Measurement_Excel_Filer.exe` + `HOW TO USE.txt` (do NOT send `settings.json` or `Excel Backups`)
- `brainstorms/` — this file
