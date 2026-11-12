# Homescreen18 1.0 implementation audit
Source deb SHA256: 27e1edd936f0eeee790c6cd7345e57650a58250bca0f164ccad1bfb0c3a42ff6.
Static analysis, arm64 slice. No original code is loaded into SpringBoard.

Verified entry points:
- I18Settings +colorWithHue:panelBrightness: 0xfa34: p<=0.5: S=.75, V=.55+.9*p; otherwise S=1.5*(1-p), V=1.
- I18Effects -applyTintEffect:bundleID:color: 0x16d50: bundled art via I18Solstice; generic fallback uses original icon. Calendar and Apple Maps have separate branches.
- I18TintSolsticeImage 0x12d70 / I18TintFullImage 0x12adc share loop 0x12b70. Prepared art enables neutral-background restoration. Generic input does not.
- Pixel helper 0x1374c: L=.2126R+.7152G+.0722B; output HSV uses chosen H,S and V=max(selected V,.55)*clamp(.22+.78*L,.12,1). S<.05 outputs grayscale.
- Prepared restoration: (1-smoothstep(.26,.38,L))*(1-smoothstep(.20,.34,source S)); enabled for source alpha>=.08. Mix unpremultiplied original RGB with tinted RGB. Alpha<=4/255 is removed. Colored HSV output is opaque; grayscale preserves source alpha.
- Whole-loop ARM64 emulation is in oracle.py; 400 deterministic test cases cover both paths. fixtures.json holds inputs and exact output bytes. Independently implemented C matched all 400 byte-for-byte on the Linux host before fixture export.

Panel evidence:
- Uses its own I18CustomizationPanel UIViewController, stack views and native sheet custom detent (the latter is an iOS16+ API).
- configureSheet:tinted: 0x22270: corner radius28, hidden grabber, largest-undimmed detent equals selected detent.
- viewDidLoad 0x22a80: blur style7, native size segmented control width200 height32, regular13 font, mode stack spacing6, root spacing8, custom gaps14/32/32.
- I18ModeButton layout 0x2062c: outer74.5 square, artwork inset4.25 ->66 square, rounded radius15, caption baseline uses font metrics and12pt gap.
- Height: preferred mode button height+72+26 (plain); +72+136+30 (tinted).

Remaining parity audit before a claim of complete equivalence:
- Maps-only-blue special branch; icon-specific detail restoration.
- Calendar rendering and fallback dark-icon segmentation.
- Full panel constraints, haptics, touch tracking, and iOS15 presentation equivalent.
- On-device runtime coverage (switcher, notifications, folders, Settings, Spotlight).
