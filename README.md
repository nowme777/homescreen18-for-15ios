# IconTint15: macOS build kit

Place these two files in a repository accessible to the GitHub connection:
`.github/workflows/build.yml` and `patches/18style.patch`.
The workflow starts on pushes to main and can also be run manually from Actions. It checks out the pinned 26Home source,
applies the adaptation, and builds using macOS/Apple clang. No release is published.

The artifact is a BINARY BASE ONLY, not the final installable package: the private
Home18 artwork will be combined locally after retrieving the built artifact. Do not
install that intermediate artifact. The user-supplied artwork is not uploaded to GitHub.

Upstream: ngkhoi / ngkoi, https://github.com/ngkoi/26Home
Commit: 3b9378591c1c7d69d79080d130fa0d3dd2b358a1
Code license: CC BY-NC-SA 4.0. The original LICENSE is retained by the build.

This workflow has been prepared and reviewed locally, but has not been run.
The earlier SpringBoard freezes remain unexplained. No claim of a confirmed fix.
