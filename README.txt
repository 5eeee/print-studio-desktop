Print Studio 0.4.0 — Windows x64

PDF, JPEG, PNG, TIFF, BMP, WebP; red/white UI, preview, fit/fill and copies.
Automatic print path is model-specific RAW PostScript for Xerox C7000 PS queues.
Source: https://github.com/5eeee/print-studio-desktop

The application requests Glossy Cardstock or Plain and Enhanced using the exact
PostScript commands in Xerox C7000 Generic PPD 5.739.0.0:
https://www.support.xerox.com/en-us/product/versalink-c7000/content/148618
The Xerox manual associates Enhanced with 1200 x 2400 dpi device output.
Print pages use lossless RGB raster tiles sampled at 1200 x 2400 per inch.
No 600 ppi intermediate print stage. Small source photos do not gain detail.

Queue RAW support is checked before submission. Windows accepting a spool job
is NOT confirmation that hardware printed it or honoured all settings.
Physical Xerox acceptance, vendor PostScript commands, media, margins and duplex
must be checked on the customer's device. No physical device is available here.
This release does not automatically configure physical trays or bypass paper prompts.
Xerox properties need not open: this path bypasses driver rendering filters.
No print queue defaults are changed. No automatic fallback to a different mode.

Automatic size range is conservatively 105–297 x 148–432 mm, also rotated.
Duplex in this release is limited to ordinary A3/A4/A5 paper; 170 gsm glossy is blocked.
Page range input supports 1-3, 5, 8. Empty range prints all pages. Test one page first.
Image fill crops centrally; fit keeps the whole image. No manual crop positioning yet.
Memory is bounded by tile size; temporary jobs can be large. 2 billion pixel job limit.
Device non-printable borders remain. Zero layout margin does not imply borderless.

Scan diagnostics copy capabilities only, not documents or private parameter payloads.
No telemetry or document uploads. Temporary raster jobs are deleted after spooling.
Close old window before updating. Installation is per-user with a desktop shortcut.
Dependencies: PySide6, PyMuPDF, pywin32. Source AGPL-3.0-or-later.
