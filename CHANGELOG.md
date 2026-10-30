# Print Studio

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
