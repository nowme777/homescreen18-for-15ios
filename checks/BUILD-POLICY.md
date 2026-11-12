# Build policy for IconTint15 / Homescreen18 for iOS15

Explicit user instruction: compile native binaries on macOS only.
The Linux cross-build 0.3.0~test0linux1 caused SpringBoard to hang on the user's iPhone XS / iOS15.2.1. The user recovered and removed it. The cause has not been established; matching CPU subtype, deployment target, pointer format and valid signatures did not prevent the failure.

Do not compile or offer another Linux native build. assemble_linux_release.py is disabled. The Drive file was renamed NOT-FOR-INSTALL in Russian.

Fetch a successful macOS GitHub Actions artifact for the exact source revision. Keep its provenance. It is acceptable to add the user-supplied PNG resources and package a deb in this Linux workspace only when the native binary bytes are preserved and checked against the macOS artifact. Use assemble_release.py, which requires Apple/Xcode provenance.
