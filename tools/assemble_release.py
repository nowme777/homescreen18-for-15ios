#!/usr/bin/env python3
"""Combine an authenticated macOS build artifact with the local user-supplied artwork.

This does not compile, patch, or re-sign Mach-O files. It preserves the native
binaries produced by the recorded GitHub Actions run, then builds a rootless deb.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import plistlib
import shutil
import struct
import subprocess
import tarfile
import tempfile
import zipfile

VERSION = "0.3.1~test1"

POSTINST = r'''#!/bin/sh
set -eu
case "${1:-configure}" in
    configure)
        pack_root="/var/jb/Library/Application Support/26Home/IconPacks"
        printf '%s\n' 'IconTint15: configuring icon-pack directory...'
        if [ ! -d "$pack_root" ]; then
            printf '%s\n' 'IconTint15: icon-pack directory is missing.' >&2
            exit 1
        fi
        # Packaged files already have readable 0644/0755 modes. Only this
        # directory needs mobile ownership so that the manager can add packs.
        chown mobile:mobile "$pack_root"
        chmod 755 "$pack_root"
        printf '%s\n' 'IconTint15: setup complete.'
        ;;
esac
exit 0
'''


def check_macho(data):
    magic, count = struct.unpack_from(">II", data)
    if magic != 0xCAFEBABE or count != 2:
        raise ValueError("Expected a universal arm64/arm64e binary")
    architectures = set()
    for index in range(count):
        cpu, subtype, offset, length, alignment = struct.unpack_from(">IIIII", data, 8 + index * 20)
        if cpu != 0x100000C or offset + length > len(data):
            raise ValueError("Invalid ARM64 slice")
        architectures.add(subtype & 0xFFFFFF)
        image = data[offset:offset + length]
        header = struct.unpack_from("<IIIIIIII", image)
        if header[0] != 0xFEEDFACF or header[3] != 6:
            raise ValueError("Expected MH_DYLIB")
        position = 32
        deployment = signature = False
        for _ in range(header[4]):
            command, size = struct.unpack_from("<II", image, position)
            if size < 8 or position + size > len(image):
                raise ValueError("Invalid load command")
            if command == 0x32:
                platform, minimum = struct.unpack_from("<II", image, position + 8)
                if platform != 2 or minimum != 0xF0000:
                    raise ValueError("Expected an iOS 15.0 deployment target")
                deployment = True
            if command == 0x1D:
                start, size_signature = struct.unpack_from("<II", image, position + 8)
                if not size_signature or start + size_signature > len(image):
                    raise ValueError("Invalid code-signature region")
                if struct.unpack_from(">I", image, start)[0] != 0xFADE0CC0:
                    raise ValueError("Expected embedded code signature")
                signature = True
            position += size
        if not (deployment and signature):
            raise ValueError("Missing deployment/signature load commands")
    if architectures != {0, 2}:
        raise ValueError("Expected arm64 and arm64e")


def assemble(artifact, artwork, destination, license_path):
    license_bytes = license_path.read_bytes()
    if b"Attribution-NonCommercial-ShareAlike 4.0" not in license_bytes:
        raise ValueError("Expected the original 26Home code license")
    manifest = json.loads((artwork / "IMPORT-MANIFEST.json").read_text())
    if manifest["imported_pngs"] != 4165:
        raise ValueError("Unexpected artwork manifest")
    identifiers = set()
    for icon in manifest["icons"]:
        if Path(icon["filename"]).name != icon["filename"]:
            raise ValueError("Invalid artwork filename")
        data = (artwork / "Dark" / icon["filename"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != icon["sha256"]:
            raise ValueError("Artwork hash mismatch")
        if icon["bundle_id"] in identifiers:
            raise ValueError("Duplicate artwork identifier")
        identifiers.add(icon["bundle_id"])
    if len(identifiers) != 4165:
        raise ValueError("Incomplete artwork index")

    with tempfile.TemporaryDirectory(prefix="icon18-assemble-") as temporary:
        temp = Path(temporary)
        with zipfile.ZipFile(artifact) as archive:
            debs = [name for name in archive.namelist() if name.endswith(".deb")]
            if len(debs) != 1:
                raise ValueError("Expected exactly one binary-base package")
            base = temp / "base.deb"
            base.write_bytes(archive.read(debs[0]))
            provenance = [name for name in archive.namelist() if name.endswith("BUILD-PROVENANCE.txt")]
            if len(provenance) != 1:
                raise ValueError("Missing macOS build provenance")
            provenance_bytes = archive.read(provenance[0])
            if b"Apple clang version" not in provenance_bytes or b"Xcode" not in provenance_bytes:
                raise ValueError("Expected Apple toolchain provenance")

        control = subprocess.check_output(["dpkg-deb", "--field", str(base)], text=True)
        if "Package: local.icontint15.26base\n" not in control:
            raise ValueError("Unexpected binary-base package ID")
        # Check payload paths before asking dpkg to materialize them.
        tar_bytes = subprocess.check_output(["dpkg-deb", "--fsys-tarfile", str(base)])
        with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as archive:
            for member in archive:
                path = member.name.removeprefix("./").rstrip("/")
                if ".." in Path(path).parts or path.startswith("/"):
                    raise ValueError("Invalid payload path")
                if member.isfile() and not path.startswith("var/jb/"):
                    raise ValueError("Found a non-rootless file")
        stage = temp / "stage"
        subprocess.run(["dpkg-deb", "--raw-extract", str(base), str(stage)], check=True)
        binaries = [
            stage / "var/jb/Library/MobileSubstrate/DynamicLibraries/26Home.dylib",
            stage / "var/jb/Library/PreferenceBundles/26HomePrefs.bundle/26HomePrefs",
        ]
        hashes = {}
        for binary in binaries:
            check_macho(binary.read_bytes())
            hashes[str(binary.relative_to(stage))] = hashlib.sha256(binary.read_bytes()).hexdigest()

        pack = stage / "var/jb/Library/Application Support/26Home/IconPacks/Home18"
        shutil.copytree(artwork, pack, dirs_exist_ok=True)
        # The selected Home18 pack has its own clock/calendar templates. The full
        # upstream iOS 26 artwork is unused here and would duplicate about 27 MiB.
        unused_pack = stage / "var/jb/Library/Application Support/26Home/SolidGlass"
        if unused_pack.exists():
            shutil.rmtree(unused_pack)
        (pack / "BUILD-PROVENANCE.txt").write_bytes(provenance_bytes)
        (pack / "NATIVE-BINARY-SHA256.json").write_text(json.dumps(hashes, indent=2))
        # The public upstream source omits the entry included in its release deb.
        # Add this resource during assembly without changing either native binary.
        preferences_info = plistlib.loads((binaries[1].parent / "Info.plist").read_bytes())
        if preferences_info["NSPrincipalClass"] != "Home26PrefsRootListController":
            raise ValueError("Unexpected preferences principal class")
        entry = stage / "var/jb/Library/PreferenceLoader/Preferences/26HomePrefs.plist"
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_bytes(plistlib.dumps({"entry": {"bundle": "26HomePrefs", "cell": "PSLinkCell",
            "detail": "Home26PrefsRootListController", "isController": True, "label": "IconTint15"}}))
        documents = stage / "var/jb/usr/share/doc/local.icontint15.26base"
        documents.mkdir(parents=True, exist_ok=True)
        (documents / "LICENSE-26Home.txt").write_bytes(license_bytes)
        (documents / "ATTRIBUTION.md").write_text(
            "# IconTint15 — adaptation of 26Home\n\n"
            "Original author: ngkhoi / ngkoi.\n"
            "Source: https://github.com/ngkoi/26Home\n"
            "Upstream commit: 3b9378591c1c7d69d79080d130fa0d3dd2b358a1.\n"
            "Code license: CC BY-NC-SA 4.0; noncommercial adaptation under the same terms.\n\n"
            "Changes: iOS 15 target, iOS 18 menu routing, removal of active glass/blur/specular effects, "
            "separate preferences and notifications, Russian mode labels, and Home18 artwork import.\n"
            "The original Homescreen18 executable and its installation scripts are not used.\n"
            "Third-party artwork supplied by the user is not relicensed by the code license.\n")
        control_path = stage / "DEBIAN/control"
        # Avoid spawning a chmod process for each of thousands of images and
        # avoid traversing unrelated user-created packs left by upstream.
        (stage / "DEBIAN/postinst").write_text(POSTINST)
        fields = control_path.read_text().splitlines()
        fields = [line for line in fields if not line.startswith(("Version:", "Installed-Size:", "Depends:", "Description:"))]
        fields += [f"Version: {VERSION}",
                   "Depends: firmware (>= 15.0), firmware (<< 16.0), mobilesubstrate, preferenceloader",
                   "Description: Experimental iOS 18-style icon customization for iOS 15, based on 26Home."]
        # Avoid preserving a now-stale Installed-Size from the binary base.
        size_kib = sum(path.stat().st_size for path in stage.rglob("*") if path.is_file()) // 1024 + 1
        fields.append(f"Installed-Size: {size_kib}")
        control_path.write_text("\n".join(fields) + "\n")
        for directory, _, filenames in os.walk(stage):
            Path(directory).chmod(0o755)
            for filename in filenames:
                path = Path(directory) / filename
                executable = path in binaries or (path.parent.name == "DEBIAN" and filename in {"postinst", "preinst", "postrm", "prerm"})
                path.chmod(0o755 if executable else 0o644)
        for binary in binaries:
            relative = str(binary.relative_to(stage))
            if hashlib.sha256(binary.read_bytes()).hexdigest() != hashes[relative]:
                raise ValueError("Native binary changed during artwork assembly")
        destination.mkdir(parents=True, exist_ok=True)
        output = destination / f"local.icontint15.26base_{VERSION}_iphoneos-arm64.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(stage), str(output)], check=True)
        print(json.dumps({"package": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                          "application_icon_ids": len(identifiers), "native_binaries_unchanged": True}, indent=2))
        return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("artwork", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--license", type=Path, default=Path(__file__).resolve().parents[1] / "26Home-upstream/LICENSE")
    args = parser.parse_args()
    assemble(args.artifact, args.artwork, args.output, args.license)
