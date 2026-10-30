Print Studio 0.1 — Windows x64

PDF, JPEG, PNG, TIFF, BMP, WebP. Red/white interface, page preview,
custom dimensions in mm, fit/fill, sheet rotation, copies and duplex.
Use Xerox V4 PS driver properties in the print dialog for media and Enhanced quality.
The media profile in the sidebar is a reminder and duplex guard, not a Xerox media command.
Driver may normalize custom sizes. Verify paper size in its properties before printing.
Documents are rendered to raster at up to 600 ppi, capped at 40 million pixels/page.
This version does not promise a vector-preserving 1200x2400 pipeline or borderless printing.
Qt driver dialog can override sheet/copies/duplex settings; inspect its final values.
Physical Xerox output, toner adhesion, margins and duplex require acceptance at the device.
Do not duplex 170 gsm glossy on C7000. No tray hardware configuration is changed.
No document upload or telemetry. Source: print_studio.py.
Dependencies: PySide6 (LGPL/GPL/commercial), PyMuPDF (AGPL/commercial).
Application source distributed under AGPL-3.0-or-later.
Run PrintStudio.exe from its folder; keep _internal next to it.
