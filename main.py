import uvicorn
from fastapi import FastAPI

from api.routes import router

app = FastAPI(
    title="Regex Scanner API",
    version="1.0.0",
    description=(
        "A content scanning service that fetches text from various sources "
        "(websites, local files, remote source code) and applies regex patterns "
        "to detect matches — such as outbound links in HTML or import statements in code.\n\n"
        "## Use cases\n\n"
        "**Link extraction** — send a URL with an `<a href>` pattern to identify "
        "all outbound links on a page, useful for detecting sites that link to "
        "suspicious or blacklisted destinations.\n\n"
        "**Malicious package detection** — send a source code file (local or from GitHub) "
        "with import-statement patterns to enumerate third-party dependencies and flag "
        "potentially malicious packages."
    ),
    contact={"name": "Noma Home Task"},
    license_info={"name": "Private"},
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
