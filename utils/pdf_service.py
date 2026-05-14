import fitz


def extract_chapters(pdf_bytes: bytes) -> list[dict]:
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = [(i + 1, pdf[i].get_text()) for i in range(len(pdf))]

    chapters = []
    current_title = None
    current_text = ""
    start_page = 1

    for page_num, text in pages:
        lines = text.strip().split("\n")
        first_line = lines[0].strip() if lines else ""

        if _is_chapter_header(first_line) and current_text.strip():
            chapters.append({
                "title": current_title or f"Chapter {len(chapters) + 1}",
                "text": current_text.strip(),
                "page_start": start_page,
                "page_end": page_num - 1,
            })
            current_title = first_line[:100]
            current_text = text
            start_page = page_num
        else:
            if current_title is None:
                current_title = first_line[:100] if first_line else f"Chapter {len(chapters) + 1}"
            current_text += "\n" + text

    if current_text.strip():
        chapters.append({
            "title": current_title or f"Chapter {len(chapters) + 1}",
            "text": current_text.strip(),
            "page_start": start_page,
            "page_end": len(pdf),
        })

    if not chapters:
        chapters.append({
            "title": "Full Document",
            "text": "\n".join(p[1] for p in pages),
            "page_start": 1,
            "page_end": len(pdf),
        })

    return chapters


def _is_chapter_header(line: str) -> bool:
    import re
    patterns = [
        r"^(chapter|bab|bagian|section)\s+\d+",
        r"^\d+\.\s+[A-Z]",
        r"^[IVX]+\.\s+[A-Z]",
        r"^CHAPTER\s+\d+",
    ]
    return any(re.match(p, line, re.IGNORECASE) for p in patterns)
