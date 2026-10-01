# 07: PDF and DOCX extraction

**What to build:** Drop a real PDF or Word document into a session and watch it reach ready with a sensible chunk count. PDF chunks know which page they came from, so later citations can point somewhere meaningful. A scanned PDF with no text layer fails loudly rather than becoming a ready document with nothing in it.

**Blocked by:** 06 (Upload and ingest text-format documents)

**Status:** done

- [x] A text-based PDF uploads, extracts, and reaches ready with a sensible chunk count
- [x] A DOCX file uploads, extracts, and reaches ready
- [x] PDF chunks carry a page locator identifying the page they came from
- [x] A scanned PDF with no text layer fails with an explicit "no extractable text" error rather than reaching ready with zero chunks
- [x] A corrupt or password-protected PDF fails with a clear reason instead of sitting in processing forever
- [x] A large PDF completes without blocking or timing out the upload request
