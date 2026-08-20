"""Call the actual export endpoint handler directly with a real DB session."""
import sys
import asyncio

sys.path.insert(0, r"C:\GitHub\3A\backend")

DOC_ID = "efd4c750-7628-4224-a0ba-37d309515f2c"


async def main():
    from app.database import AsyncSessionLocal
    from app.api.routers.documents import export_markdown, export_docx, export_full_package_docx

    async with AsyncSessionLocal() as db:
        for fn in (export_markdown, export_docx, export_full_package_docx):
            try:
                resp = await fn(DOC_ID, db)
                body = resp.body
                print(fn.__name__, "-> OK, bytes:", len(body))
            except Exception as e:
                import traceback
                print(fn.__name__, "-> EXCEPTION:", type(e).__name__, str(e))
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())