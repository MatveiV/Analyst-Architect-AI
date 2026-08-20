"""Reproduce the export/markdown endpoint logic exactly and print any exception."""
import sys
import asyncio
import json

sys.path.insert(0, r"C:\GitHub\3A\backend")

DOC_ID = "efd4c750-7628-4224-a0ba-37d309515f2c"


async def main():
    from app.database import AsyncSessionLocal
    from app.models.document import Document
    from app.models.review import Review
    from app.models.adr_record import ADRRecord
    from app.models.diagram_artifact import DiagramArtifact
    from sqlalchemy import select, desc

    async with AsyncSessionLocal() as db:
        doc = (await db.execute(select(Document).where(Document.id == DOC_ID))).scalar_one_or_none()
        review = (await db.execute(
            select(Review).where(Review.document_id == DOC_ID).order_by(desc(Review.created_at)).limit(1)
        )).scalar_one_or_none()
        adr = (await db.execute(
            select(ADRRecord).where(ADRRecord.document_id == DOC_ID).order_by(desc(ADRRecord.created_at)).limit(1)
        )).scalar_one_or_none()
        diagrams = (await db.execute(
            select(DiagramArtifact).where(DiagramArtifact.document_id == DOC_ID)
        )).scalars().all()

        lines = [
            f"# {doc.title}",
            "",
            f"> **Type**: {doc.doc_type}  |  **Project**: {doc.project_name or '—'}  |  **Created**: {doc.created_at.isoformat()}",
            "",
            "---",
            "",
        ]

        if doc.doc_type != "markdown":
            lines += ["## Source Text", "", doc.text, ""]
        else:
            lines += [doc.text, ""]

        if review:
            review_data = json.loads(review.review_json)
            lines += ["---", "", "## Review", "",
                      f"- **Confidence**: {review_data.get('confidence', '—')}",
                      f"- **Needs Review**: {'Yes' if review_data.get('needs_review') else 'No'}", ""]
            if review_data.get("summary"):
                lines += ["### Summary", "", review_data["summary"], ""]
            if review_data.get("risks"):
                lines += ["### Risks", ""]
                for r in review_data["risks"]:
                    lines += [f"- **[{r.get('severity', '').upper()}]** {r.get('description', '')}"]
                lines.append("")

        if adr:
            adr_data = json.loads(adr.adr_json)
            lines += ["---", "", "## Architectural Decision Record (ADR)", "",
                      f"**{adr_data.get('title', '')}**", "",
                      f"**Status**: {adr_data.get('status', 'proposed')}", "",
                      "### Context", "", adr_data.get("context", ""), "",
                      "### Problem", "", adr_data.get("problem", ""), "",
                      "### Decision", "", adr_data.get("decision", ""), ""]

        if diagrams:
            lines += ["---", "", "## Diagrams", ""]
            for d in diagrams:
                lang = "mermaid" if d.notation == "mermaid" else "plantuml"
                lines += [f"### {d.diagram_type} ({d.notation})", "", f"```{lang}", d.source_code, "```", ""]

        md = "\n".join(lines)
        print("MARKDOWN LENGTH:", len(md))
        print(md[:600])


if __name__ == "__main__":
    asyncio.run(main())