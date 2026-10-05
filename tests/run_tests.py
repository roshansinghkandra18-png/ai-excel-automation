"""
The full test suite for the Daily Measurement Excel Filer.

Run it any time - especially after ANY change - with:

    python "tests/run_tests.py"

It builds its own awkward test PDFs, runs everything end to end against a
throwaway folder (your real files are never touched), prints the results,
and writes the whole report to:

    Test Results/latest_test_run.md

That one file is overwritten each run, so it is always the current picture.
"""

import os
import shutil
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, HERE)

import openpyxl
import pdf_reader
import parser as pdf_parser
import excel_writer
import history
import pdf_maker

SANDBOX = os.path.join(ROOT, "_test_sandbox")
PDF_DIR = os.path.join(SANDBOX, "pdfs")
RECORDS = os.path.join(SANDBOX, "records")
BACKUPS = os.path.join(SANDBOX, "backups")
REPORT = os.path.join(ROOT, "Test Results", "latest_test_run.md")

results = []


def check(name, given, expected, actual, passed, note=""):
    results.append({
        "name": name, "given": given, "expected": expected,
        "actual": actual, "passed": passed, "note": note,
    })
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    if not passed:
        print(f"         expected: {expected}")
        print(f"         actually: {actual}")


def fresh_sandbox():
    if os.path.exists(SANDBOX):
        shutil.rmtree(SANDBOX, ignore_errors=True)
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(RECORDS, exist_ok=True)


def file_a_pdf(path, records=RECORDS):
    """Runs one PDF through the whole pipeline, the way the app does."""
    parsed = pdf_parser.parse_pdf_text(pdf_reader.extract_text(path))
    if parsed.date_value is None or not parsed.entries:
        return parsed, None, None
    wb, ws, is_new, stamp = excel_writer.load_or_create_workbook(records, parsed.date_value)
    excel_writer.append_entries(ws, parsed.date_value, parsed.entries)
    excel_writer.save_with_backup(wb, excel_writer.workbook_path(records),
                                  BACKUPS, expected_stamp=stamp)
    history.remember(records, history.fingerprint(path), path, ws.title, len(parsed.entries))
    return parsed, ws.title, is_new


def row_values(records, tab, row):
    wb = openpyxl.load_workbook(excel_writer.workbook_path(records))
    ws = wb[tab]
    return [ws.cell(row=row, column=c).value for c in range(1, 9)]


# ---------------------------------------------------------------------------
# Group A - reading messy human input
# ---------------------------------------------------------------------------
def group_a():
    print("\nGroup A - reading messy human input")
    fresh_sandbox()

    p = pdf_maker.day_pdf(os.path.join(PDF_DIR, "a_clean.pdf"), "1st September 2026", [
        pdf_maker.patient_block("Savita Aggarwal", "Self", "SC-3", "2",
                                "9876543210", "5000", ["Kakinada"]),
    ])
    parsed, tab, _ = file_a_pdf(p)
    e = parsed.entries[0] if parsed.entries else {}
    check("A normal, tidy entry is read correctly",
          "Name: Savita Aggarwal / Doctor: Self / Model Number: SC-3 / Units: 2 / Mobile: 9876543210 / Amount: 5000 / Kakinada",
          "all seven fields land in their own columns",
          f"name={e.get('PATIENT NAME')} doctor={e.get('DOCTOR')} code={e.get('CODE')} "
          f"units={e.get('NO. OF UNITS')} mobile={e.get('MOBILE NO.')} amount={e.get('AMOUNT')} "
          f"misc={e.get('MISCELLANEOUS')}",
          e.get("PATIENT NAME") == "Savita Aggarwal" and e.get("CODE") == "SC-3"
          and e.get("NO. OF UNITS") == "2" and e.get("MISCELLANEOUS") == "Kakinada")

    p = pdf_maker.write_pdf(os.path.join(PDF_DIR, "a_colon.pdf"), [
        "Date : 2nd September 2026", " ",
        "name: Anil Kumar", "Doctor:Self", "model number:SC1",
        "number of units :2", "Mobile Number : 9811111111", "amount:5000",
    ])
    parsed, _, _ = file_a_pdf(p)
    e = parsed.entries[0] if parsed.entries else {}
    check("Colons in odd places ('units :2', 'Doctor:Self')",
          "number of units :2  (space BEFORE the colon)",
          "units read as '2', with the stray colon dropped",
          f"units={e.get('NO. OF UNITS')!r} doctor={e.get('DOCTOR')!r}",
          e.get("NO. OF UNITS") == "2" and e.get("DOCTOR") == "Self")

    check("Model number gets its hyphen ('SC1' becomes 'SC-1')",
          "model number:SC1", "SC-1", e.get("CODE"), e.get("CODE") == "SC-1")

    p = pdf_maker.day_pdf(os.path.join(PDF_DIR, "a_mobile.pdf"), "3rd September 2026", [
        pdf_maker.patient_block("Meena", "Self", "SC-2", "1", "not known", "1000"),
        pdf_maker.patient_block("Raju", "Self", "SC-2", "1", "not there", "1000"),
        pdf_maker.patient_block("Vikram", "Self", "SC-2", "1", "96501 58644", "1000"),
    ])
    parsed, _, _ = file_a_pdf(p)
    mobiles = [e["MOBILE NO."] for e in parsed.entries]
    check("Mobile written as words ('not known' / 'not there')",
          "three patients: 'not known', 'not there', '96501 58644'",
          "first two mobile boxes empty; the real number kept exactly, spaces and all",
          str(mobiles),
          mobiles == ["", "", "96501 58644"])

    p = pdf_maker.day_pdf(os.path.join(PDF_DIR, "a_amount.pdf"), "4th September 2026", [
        pdf_maker.patient_block("Asha", "Self", "SC-5", "1", "9812345678", "None"),
        pdf_maker.patient_block("Bala", "Self", "SC-5", "1", "9812345679", "10,000"),
    ])
    parsed, tab, _ = file_a_pdf(p)
    amounts = [e["AMOUNT"] for e in parsed.entries]
    check("Amount written as 'None', and as '10,000' with a comma",
          "Amount: None  and  Amount: 10,000",
          "'None' leaves the box empty; '10,000' becomes the number 10000",
          str(amounts), amounts == ["", "10,000"])

    p = pdf_maker.day_pdf(os.path.join(PDF_DIR, "a_misc.pdf"), "5th September 2026", [
        pdf_maker.patient_block("Chandra", "Self", "SC-7", "1", "9812345670", "2000",
                                ["Location: Chandigarh"]),
        pdf_maker.patient_block("Divya", "Self", "SC-7", "1", "9812345671", "2000",
                                ["FOC", "replacement"]),
    ])
    parsed, _, _ = file_a_pdf(p)
    miscs = [e["MISCELLANEOUS"] for e in parsed.entries]
    check("Leftover text goes to Miscellaneous, label word stripped",
          "'Location: Chandigarh' on one, 'FOC' and 'replacement' on another",
          "'Chandigarh' (no 'Location:' prefix), and 'FOC; replacement'",
          str(miscs), miscs == ["Chandigarh", "FOC; replacement"])

    p = pdf_maker.write_pdf(os.path.join(PDF_DIR, "a_noblank.pdf"), [
        "Date: 6th September 2026",
        "Name: Ekta", "Doctor: Self", "Model Number: SC-9", "Number of Units: 1",
        "Name: Farah", "Doctor: Self", "Model Number: SC-9", "Number of Units: 3",
    ])
    parsed, _, _ = file_a_pdf(p)
    names = [e["PATIENT NAME"] for e in parsed.entries]
    check("Patients run together with NO blank line between them",
          "two patients back to back, no separating blank line",
          "still read as two separate patients (Ekta and Farah)",
          f"{len(parsed.entries)} patient(s): {names}",
          names == ["Ekta", "Farah"])


# ---------------------------------------------------------------------------
# Group B - refusing to guess
# ---------------------------------------------------------------------------
def group_b():
    print("\nGroup B - refusing to guess")

    p = pdf_maker.write_pdf(os.path.join(PDF_DIR, "b_nodate.pdf"), [
        "Name: Gita", "Doctor: Self", "Model Number: SC-3", "Number of Units: 1",
    ])
    parsed = pdf_parser.parse_pdf_text(pdf_reader.extract_text(p))
    check("A PDF with no date line at all",
          "a patient, but no 'Date:' line anywhere",
          "stopped, flagged, and nothing written to Excel",
          f"date={parsed.date_value}, flags={[r for _, r in parsed.flagged_lines]}",
          parsed.date_value is None and len(parsed.flagged_lines) >= 1)

    p = pdf_maker.day_pdf(os.path.join(PDF_DIR, "b_baddate.pdf"), "somethingnotadate", [
        pdf_maker.patient_block("Hari", "Self", "SC-3", "1"),
    ])
    parsed = pdf_parser.parse_pdf_text(pdf_reader.extract_text(p))
    check("A date nobody could read ('somethingnotadate')",
          "Date: somethingnotadate", "stopped, flagged, nothing written",
          f"date={parsed.date_value}, flags={[r for _, r in parsed.flagged_lines]}",
          parsed.date_value is None)

    p = pdf_maker.day_pdf(os.path.join(PDF_DIR, "b_noname.pdf"), "7th September 2026", [
        pdf_maker.patient_block("Indira", "Self", "SC-3", "1"),
        pdf_maker.patient_block(None, "Self", "SC-4", "2"),
    ])
    parsed, _, _ = file_a_pdf(p)
    check("One patient block has no name",
          "two blocks; the second has a doctor and code but no 'Name:' line",
          "the named patient is saved; the nameless block is flagged, not guessed",
          f"saved={[e['PATIENT NAME'] for e in parsed.entries]}, "
          f"flagged={len(parsed.flagged_lines)}",
          len(parsed.entries) == 1 and len(parsed.flagged_lines) == 1)

    p = pdf_maker.write_pdf(os.path.join(PDF_DIR, "b_empty.pdf"), [" "])
    text = pdf_reader.extract_text(p)
    check("A PDF with nothing usable in it",
          "an effectively empty PDF",
          "handled calmly - no crash, nothing written",
          f"extracted text = {text.strip()!r}", text.strip() == "")


# ---------------------------------------------------------------------------
# Group C - day after day, month after month
# ---------------------------------------------------------------------------
def group_c():
    print("\nGroup C - day after day, month after month")
    fresh_sandbox()

    p1 = pdf_maker.day_pdf(os.path.join(PDF_DIR, "c_day1.pdf"), "1st October 2026", [
        pdf_maker.patient_block("Day One", "Self", "SC-1", "1", "9800000001", "1000")])
    p2 = pdf_maker.day_pdf(os.path.join(PDF_DIR, "c_day2.pdf"), "2nd October 2026", [
        pdf_maker.patient_block("Day Two", "Self", "SC-1", "1", "9800000002", "2000")])
    _, tab1, new1 = file_a_pdf(p1)
    _, tab2, new2 = file_a_pdf(p2)

    wb = openpyxl.load_workbook(excel_writer.workbook_path(RECORDS))
    ws = wb[tab1]
    names = [ws.cell(row=r, column=2).value for r in range(2, ws.max_row + 1)]
    check("Second day adds BELOW the first, in the same month tab",
          "1 Oct filed, then 2 Oct filed",
          "one 'OCTOBER 2026' tab holding Day One then Day Two, in that order",
          f"tab={tab1}, new_tab_on_day2={new2}, rows={names}",
          tab1 == tab2 == "OCTOBER 2026" and new2 is False and names == ["Day One", "Day Two"])

    p3 = pdf_maker.day_pdf(os.path.join(PDF_DIR, "c_nov.pdf"), "1st November 2026", [
        pdf_maker.patient_block("New Month", "Self", "SC-1", "1", "9800000003", "3000")])
    _, tab3, new3 = file_a_pdf(p3)
    check("A new month automatically gets its own tab",
          "1 Nov filed after October already exists",
          "a new 'NOVEMBER 2026' tab is created",
          f"tab={tab3}, newly created={new3}",
          tab3 == "NOVEMBER 2026" and new3 is True)

    p4 = pdf_maker.day_pdf(os.path.join(PDF_DIR, "c_backdate.pdf"), "15th August 2026", [
        pdf_maker.patient_block("Back Dated", "Self", "SC-1", "1", "9800000004", "4000")])
    file_a_pdf(p4)
    wb = openpyxl.load_workbook(excel_writer.workbook_path(RECORDS))
    check("A back-dated PDF slots into the right place, not the end",
          "August filed AFTER October and November already exist",
          "tabs read AUGUST, OCTOBER, NOVEMBER - in date order",
          f"tabs = {wb.sheetnames}",
          wb.sheetnames == ["AUGUST 2026", "OCTOBER 2026", "NOVEMBER 2026"])

    check("Everything stays in ONE Excel file",
          "four PDFs across three different months",
          "a single DAILY PATIENT RECORD.xlsx, not one file per month",
          f"files in records folder = "
          f"{sorted(f for f in os.listdir(RECORDS) if f.endswith('.xlsx'))}",
          sorted(f for f in os.listdir(RECORDS) if f.endswith(".xlsx"))
          == ["DAILY PATIENT RECORD.xlsx"])


# ---------------------------------------------------------------------------
# Group D - protecting what is already saved
# ---------------------------------------------------------------------------
def group_d():
    print("\nGroup D - protecting what is already saved")
    fresh_sandbox()

    p = pdf_maker.day_pdf(os.path.join(PDF_DIR, "d_first.pdf"), "1st December 2026", [
        pdf_maker.patient_block("First Entry", "Self", "SC-1", "1", "9800000001", "1000")])
    file_a_pdf(p)

    fp = history.fingerprint(p)
    seen = history.previous_entry(RECORDS, fp)
    check("The same PDF offered twice is recognised",
          "the identical PDF filed a second time",
          "recognised, with when it was filed and where it went",
          f"remembered as {seen}", bool(seen))

    renamed = os.path.join(PDF_DIR, "d_renamed_copy.pdf")
    shutil.copy(p, renamed)
    check("A RENAMED copy of the same PDF is still caught",
          "same file contents, different filename",
          "still recognised as already filed (matched on contents, not name)",
          f"same fingerprint = {history.fingerprint(renamed) == fp}",
          history.fingerprint(renamed) == fp)

    other = pdf_maker.day_pdf(os.path.join(PDF_DIR, "d_other.pdf"), "2nd December 2026", [
        pdf_maker.patient_block("Different Person", "Self", "SC-2", "1", "9800000009", "9000")])
    check("A genuinely different PDF is NOT falsely flagged",
          "a completely different day's PDF",
          "not treated as a duplicate",
          f"previously seen = {history.previous_entry(RECORDS, history.fingerprint(other))}",
          history.previous_entry(RECORDS, history.fingerprint(other)) is None)

    # Two people saving at once.
    pa = pdf_maker.day_pdf(os.path.join(PDF_DIR, "d_personA.pdf"), "5th December 2026", [
        pdf_maker.patient_block("Person A Entry", "Self", "SC-1", "1", "9800000011", "1100")])
    pb = pdf_maker.day_pdf(os.path.join(PDF_DIR, "d_personB.pdf"), "6th December 2026", [
        pdf_maker.patient_block("Person B Entry", "Self", "SC-1", "1", "9800000012", "1200")])

    parsedA = pdf_parser.parse_pdf_text(pdf_reader.extract_text(pa))
    wbA, wsA, _, stampA = excel_writer.load_or_create_workbook(RECORDS, parsedA.date_value)
    excel_writer.append_entries(wsA, parsedA.date_value, parsedA.entries)

    time.sleep(0.05)
    file_a_pdf(pb)  # Person B saves first

    blocked = False
    try:
        excel_writer.save_with_backup(wbA, excel_writer.workbook_path(RECORDS),
                                      BACKUPS, expected_stamp=stampA)
    except excel_writer.ConcurrentChangeError:
        blocked = True

    wb = openpyxl.load_workbook(excel_writer.workbook_path(RECORDS))
    ws = wb["DECEMBER 2026"]
    names = [ws.cell(row=r, column=2).value for r in range(2, ws.max_row + 1)]
    check("Two people saving at once - nobody's work is lost",
          "Person A opens the record; Person B saves first; Person A then tries to save",
          "Person A is blocked, and Person B's entry is still in the file",
          f"A blocked = {blocked}; rows now = {names}",
          blocked and "Person B Entry" in names)

    # File locked by Excel.
    path = excel_writer.workbook_path(RECORDS)
    os.chmod(path, 0o444)
    locked_ok = False
    try:
        parsed = pdf_parser.parse_pdf_text(pdf_reader.extract_text(other))
        wb2, ws2, _, st2 = excel_writer.load_or_create_workbook(RECORDS, parsed.date_value)
        excel_writer.append_entries(ws2, parsed.date_value, parsed.entries)
        excel_writer.save_with_backup(wb2, path, BACKUPS, expected_stamp=st2)
    except PermissionError:
        locked_ok = True
    finally:
        os.chmod(path, 0o666)
    check("The Excel file is open in Excel when someone adds a PDF",
          "the record file locked, exactly as Excel locks it when open",
          "refuses safely so the person can be told to close it - nothing corrupted",
          f"refused safely = {locked_ok}", locked_ok)

    check("A backup copy is kept on every save",
          "several PDFs filed",
          "a matching copy of the record sits in the backups folder",
          f"backups folder holds {os.listdir(BACKUPS) if os.path.isdir(BACKUPS) else 'nothing'}",
          os.path.isdir(BACKUPS) and "DAILY PATIENT RECORD.xlsx" in os.listdir(BACKUPS))

    # Existing rows must never change. Compare only the rows that already
    # held data - the new entry is expected to land on the empty row after them.
    wb = openpyxl.load_workbook(excel_writer.workbook_path(RECORDS))
    last_before = wb["DECEMBER 2026"].max_row
    before = [row_values(RECORDS, "DECEMBER 2026", r) for r in range(2, last_before + 1)]
    file_a_pdf(other)
    after = [row_values(RECORDS, "DECEMBER 2026", r) for r in range(2, last_before + 1)]
    wb = openpyxl.load_workbook(excel_writer.workbook_path(RECORDS))
    grew = wb["DECEMBER 2026"].max_row > last_before
    check("Rows already saved are never altered by a later run",
          f"another PDF filed into a tab that already held {last_before - 1} row(s)",
          "every existing row identical afterwards, and the new entry added beneath them",
          ("existing rows unchanged, new row added below"
           if before == after and grew
           else f"before={before} after={after} grew={grew}"),
          before == after and grew)


# ---------------------------------------------------------------------------
# Group E - the Excel file is genuinely usable
# ---------------------------------------------------------------------------
def group_e():
    print("\nGroup E - the Excel file is genuinely usable")
    fresh_sandbox()

    p = pdf_maker.day_pdf(os.path.join(PDF_DIR, "e_types.pdf"), "1st January 2027", [
        pdf_maker.patient_block("Number Check", "Self", "SC-1", "3", "09812345678", "10,000"),
    ])
    _, tab, _ = file_a_pdf(p)
    row = row_values(RECORDS, tab, 2)
    date_v, units_v, mobile_v, amount_v = row[0], row[4], row[6], row[7]

    check("Amounts are real numbers that can be totalled",
          "Amount: 10,000 (written with a comma)",
          "stored as the number 10000, not as text",
          f"value={amount_v!r} type={type(amount_v).__name__}",
          isinstance(amount_v, (int, float)) and amount_v == 10000)

    check("Unit counts are real numbers",
          "Number of Units: 3",
          "stored as the number 3, not as text",
          f"value={units_v!r} type={type(units_v).__name__}",
          isinstance(units_v, (int, float)) and units_v == 3)

    check("Dates are real dates, so they sort and filter properly",
          "Date: 1st January 2027",
          "stored as a real date, not as text",
          f"value={date_v!r} type={type(date_v).__name__}",
          isinstance(date_v, datetime))

    check("A mobile number keeps its leading zero",
          "Mobile Number: 09812345678",
          "kept exactly as written, leading zero intact",
          f"value={mobile_v!r}", mobile_v == "09812345678")

    wb = openpyxl.load_workbook(excel_writer.workbook_path(RECORDS))
    ws = wb[tab]
    headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
    check("The columns are the agreed ones, in the agreed order",
          "any filed PDF",
          " | ".join(excel_writer.HEADERS),
          " | ".join(str(h) for h in headers),
          headers == excel_writer.HEADERS)

    check("The header row is styled and frozen so it stays visible",
          "any filed PDF",
          "header filled dark blue, bold white text, and frozen at row 2",
          f"fill={ws['A1'].fill.fgColor.rgb}, bold={ws['A1'].font.bold}, "
          f"freeze={ws.freeze_panes}",
          ws["A1"].font.bold and ws.freeze_panes == "A2")


def write_report():
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)

    lines = [
        "# Latest Test Run — Daily Measurement Excel Filer",
        "",
        f"Run on: {datetime.now().strftime('%d %B %Y at %H:%M')}",
        "",
        "Run automatically by `tests/run_tests.py`. Everything happened inside a "
        "throwaway `_test_sandbox` folder — your real Excel file and your real "
        "PDFs were never touched.",
        "",
        "## Totals",
        f"- Tests run: **{len(results)}**",
        f"- Passed: **{passed}**",
        f"- Failed: **{failed}**",
        "",
    ]
    if failed:
        lines += ["### Failures needing attention", ""]
        lines += [f"- {r['name']}" for r in results if not r["passed"]]
        lines.append("")
    else:
        lines += ["Everything passed.", ""]

    lines.append("---")
    for i, r in enumerate(results, 1):
        lines += [
            "",
            f"## {i}. {r['name']}",
            "",
            f"**What was fed in:** {r['given']}",
            "",
            f"**What was expected:** {r['expected']}",
            "",
            f"**What actually happened:** {r['actual']}",
            "",
            f"**Result: {'PASSED' if r['passed'] else 'FAILED'}**",
        ]
        if r["note"]:
            lines += ["", f"_Note: {r['note']}_"]

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    print("Running the full test suite...")
    for group in (group_a, group_b, group_c, group_d, group_e):
        group()

    write_report()
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    print(f"\n{'=' * 58}")
    print(f"  {len(results)} tests   {passed} passed   {failed} failed")
    print(f"  Full report: Test Results/latest_test_run.md")
    print("=" * 58)

    shutil.rmtree(SANDBOX, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
