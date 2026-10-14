# TableTroopers native decompilation workbench

A **partial ARM64 native matching project** for TableTroopers **2026.40.4**, versionCode **212724703**, compatible with decomp.wtf fork mode. This is not a rebuilt APK, the original C# project, or a claim of complete game recovery.

The initial three-function pilot has one exact native match: `TickHelper.TicksToSecondsFloat` (44 bytes). `WeaponTypeSwitcher.GetMaxDelta` and `WaterHandler.Update` compile but remain nonmatching. Caller-byte matching does not establish Unity runtime behavior, null-helper effects or the full game ABI.

## Setup and build

Use Linux x86_64, Python 3.12+, Ninja, and **Android NDK r27c (27.2.12479018)**. The compiler must report Clang **18.0.3**, Android build **12470979**. The original native build note identifies Android **API 25**, NDK r27c build 12479018. Optimization flags remain partially reconstructed; each pilot's calibrated profile is recorded.

Provide your own APK. Nothing here downloads or distributes the game.

```sh
git clone https://github.com/mitch030504/tabletroopers-decomp.git
cd tabletroopers-decomp
export ANDROID_NDK_HOME=/your/path/android-ndk-r27c
python3 configure.py --apk /your/path/TableTroopers.apk
ninja
python3 tools/matching.py verify --ndk "$ANDROID_NDK_HOME"
```

APK SHA-256: `70cd395e4546299127a54b2274c4f281438e267b4326b405fe301a76bc7746e4`. Setup rejects other builds and validates the extracted IL2CPP binary/metadata. Game inputs and generated objects stay in ignored `orig/` and `build/` directories. Confirm APK ownership before using decomp.wtf's import prompts.

NDK download: [Google's r27c Linux archive](https://dl.google.com/android/repository/android-ndk-r27c-linux.zip), official repository SHA-1 `090e8083a715fdb1a3e402d0763c388abb03fb4e`. Extract with a tool that preserves symlinks and permissions, such as `unzip`.

## Open in decomp.wtf

The tested application is **decompnet 0.9.8**, source commit `a8708d82246f869fddd1f9e98d4007397f31dea6`, with **objdiff-cli 3.8.2**. For its reproducible environment:

```sh
git clone https://github.com/i12bp8/decomp.wtf.git /tmp/decomp-wtf
cd /tmp/decomp-wtf
git checkout a8708d82246f869fddd1f9e98d4007397f31dea6
uv sync --locked --no-dev
uv run --locked --no-dev decomp
```

Choose **Continue a public decomp**, paste this repository URL, supply the matching APK, and follow the NDK setup above in its cloned directory. The `.decomp.wtf.json` setup generates `objdiff.json` and Ninja rules. Each unit identifies its editable C++ source. Use Git PRs to collaborate; this APK-derived project does not use decomp.wtf ROM rooms.

## What verification means

Candidate C/C++ compiles with the pinned toolchain and links at the function's original RVA. External native references are fixed by the version-specific manifest. A separate comparison checks the linked function's **entire byte sequence and size**, not just mnemonic similarity or objdiff percentages. Both target and candidate display objects are derived ET_REL containers, not recovered original object files. The target bytes come only from your private APK; candidate bytes come only from compilation/linking.

`python3 tools/matching.py report` displays pilot results. `verify` recompiles every candidate, including previous matches after a header change. Runtime and metadata/ABI limitations remain separate findings. Never mark a unit `complete`/linked merely because it matches; there is no whole-APK relink/checksum target yet.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Contributions may include reconstruction, tools, metadata corrections and reproducible validators. Preserve nonmatching candidates and unresolved evidence. Automated work is disclosed and reviewed; no automatic upstream pushes or PR merges occur.

The existing research workflow independently verifies the complete research project with Luna and Sol. This pilot supplies another evidence source, without replacing either gate.
