"""
Builds small text PDFs for the test suite.

Written by hand rather than with a PDF library, so the test suite needs
nothing installed beyond what the program itself already uses.
"""

import os


def _escape(text):
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def write_pdf(path, lines):
    """Creates a one-page PDF containing the given lines of text."""
    content_lines = ["BT", "/F1 12 Tf", "72 720 Td", "16 TL"]
    for line in lines:
        content_lines.append(f"({_escape(line)}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n").encode()

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(bytes(out))
    return path


def patient_block(name=None, doctor=None, model=None, units=None,
                  mobile=None, amount=None, extras=None):
    """Builds one patient's lines the way the office actually dictates them."""
    lines = []
    if name is not None:
        lines.append(f"Name: {name}")
    if doctor is not None:
        lines.append(f"Doctor: {doctor}")
    if model is not None:
        lines.append(f"Model Number: {model}")
    if units is not None:
        lines.append(f"Number of Units: {units}")
    if mobile is not None:
        lines.append(f"Mobile Number: {mobile}")
    if amount is not None:
        lines.append(f"Amount: {amount}")
    lines.extend(extras or [])
    return lines


def day_pdf(path, date_text, blocks, date_label="Date"):
    """A full day's PDF: the date once at the top, then a block per patient."""
    # Real PDFs put a single space on the "blank" separator line, not a truly
    # empty one, so the test files match what actually comes out of Word/Wispr.
    gap = " "
    lines = []
    if date_text is not None:
        lines.append(f"{date_label}: {date_text}")
        lines.append(gap)
    for i, block in enumerate(blocks):
        if i:
            lines.append(gap)
        lines.extend(block)
    return write_pdf(path, lines)
