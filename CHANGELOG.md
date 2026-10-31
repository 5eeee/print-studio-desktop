# Print Studio

## 0.4.3

- Compact two-column settings expose quality, duplex, copies and page range without scrolling at 960x640.
- Checked keyboard selection in all six combos, action dispatch for four buttons and rotation.
- Physical printer acceptance remains pending.

## 0.4.2

- Added explicit painted chevrons and separate dropdown hit regions.
- Refined primary/secondary buttons with line icons and disabled/pressed states.
- Removed horizontal settings overflow; verified real popup opening.
- Print backend unchanged.

## 0.4.1

- Fixed actual WebP opening with a Qt decoding fallback.
- Fixed blank PDF pages in PostScript generation.
- Closed rejected encrypted/empty documents and retained the previous document on failure.
- Added non-finite parameter rejection, atomic preference writes and malformed preference recovery.
- Decoupled queue diagnostics from invalid page ranges and document serialization.
- Always ended preview painters on failure; accepted typographic range dashes.
- Added 8 automated integration/regression tests, including mock RAW transport and end-to-end job preparation.

## 0.4.0

- Added page ranges, deduplication and bounds validation.
- Added persistent preferences and drag-and-drop opening.
- Added Standard, Enhanced and Photo vendor modes.
- Hid diagnostics behind an advanced-settings toggle.
- Disabled duplicate print submission while a job is running.
- Verified ranges, preferences, image opening and lossless raster generation.
- Physical device acceptance is still required.

## 0.3.0

- Redesigned red/white workspace, header, grouped settings and persistent print footer.
- Added responsive full-page preview and compact side-by-side dimensions.
- Checked 1200x820 and 960x640 layouts; print backend unchanged.

## 0.2.0

- Added a model-specific RAW PostScript print path for Xerox C7000 PS queues.
- Embedded the Glossy Cardstock (`cardstock-glossy`), Plain (`stationery`), Enhanced
  and duplex commands from Xerox's official C7000 PPD. No Xerox properties dialog.
- Replaced the 600 ppi capped print raster with bounded-memory, losslessly compressed
  1200 x 2400 samples/in tiles. Preview remains low resolution and is not printed.
- Added conservative size validation, glossy duplex guard, RAW transport checks,
  background job preparation and abort handling on write failure.
- Added driver capability diagnostics excluding private PrintTicket parameter values.
- Preserved old installed version by installing 0.2.0 into a separate version directory.
- Checked lossless tile sizes and decoding; rendered the raster PostScript section
  with Ghostscript; checked UI PDF/JPEG preview and duplex rejection.
- Physical C7000 output, vendor device commands and RAW acceptance on the customer's
  V4 queue are not locally verified. Spool submission is not hardware acknowledgement.
- The PrintTicket-only strict path is not used for automatic printing because this
  Xerox V4 package stores Enhanced in a private settings payload.
