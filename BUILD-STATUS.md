# IconTint15 0.2.0 test build

The macOS build completed successfully in [run 43139109942](https://github.com/nowme777/homescreen18-for-15ios/actions/runs/43139109942).

- Upstream: [ngkoi/26Home](https://github.com/ngkoi/26Home), commit `3b9378591c1c7d69d79080d130fa0d3dd2b358a1`.
- Patch: SHA-256 `41b3ef5e504f9aa7276e6ce5c90bcbb6d3a9bce63d89c2ea9b394e7f1d6d4d19`.
- Native toolchain: Xcode 16.4, Apple clang 17.0.0, iPhoneOS15.6.sdk, iOS 15.0 deployment target.
- The GitHub artifact is a binary base, not the final package for installation.
- Final assembly adds 4,165 application icons from the user-provided Homescreen18 package, a PreferenceLoader entry, and attribution. Native binaries remain byte-for-byte unchanged.
- User-provided third-party artwork is not uploaded to this repository.
- The final package conflicts with upstream `com.ngkhoi.26home` and earlier `local.icontint15` packages.

Code derived from 26Home is attributed to ngkhoi / ngkoi under CC BY-NC-SA 4.0. The code license does not relicense third-party artwork.

Build and static package checks do not establish on-device stability. The earlier SpringBoard hangs remain unexplained. The iPhone XS / iOS 15.2.1 runtime test is still pending.
