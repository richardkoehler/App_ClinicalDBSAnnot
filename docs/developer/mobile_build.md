# Mobile build guide (iOS + Android)

Mobile builds use the Toga backend (`dbs_annotator.gui.toga_backend.app`)
rather than the desktop Qt entry point. Briefcase targets are defined in
`pyproject.toml` under `[tool.briefcase.app.dbs_annotator.iOS]` /
`[tool.briefcase.app.dbs_annotator.android]`.

## Prerequisites

### iOS

- macOS host, Xcode + Command Line Tools installed.
- Apple Developer account (free tier works for simulator, paid tier
  required for on-device installs / TestFlight).
- A provisioning profile for the bundle id `ch.wysscenter.dbsannotator`.

### Android

- JDK 17.
- Android Studio installed so the Android SDK / NDK is available; set
  `ANDROID_HOME` to its location.
- A keystore file for release signing; store it in a secrets manager,
  never in the repo.

## Build commands

All commands run from the repo root.

```bash
# iOS simulator (dev loop)
uv run briefcase create iOS
uv run briefcase build iOS
uv run briefcase run iOS

# Android emulator
uv run briefcase create android
uv run briefcase build android
uv run briefcase run android
```

For release / store uploads:

```bash
uv run briefcase package iOS        # .ipa
uv run briefcase package android    # .aab
```

Release packaging on Android requires the keystore:

```bash
export ANDROID_KEYSTORE=/path/to/release.keystore
export ANDROID_KEYSTORE_PASSWORD=...
export ANDROID_KEY_ALIAS=dbs-annotator
export ANDROID_KEY_PASSWORD=...
uv run briefcase package android
```

## Runtime differences from the desktop build

The Toga app boots from `dbs_annotator.gui.toga_backend.app:main` and:

- installs the Toga GUI backend via
  `gui.toga_backend.bootstrap.install(app)`;
- uses ReportLab (`gui.toga_backend.mobile_export.write_session_pdf`)
  for PDF export -- **not** `docx2pdf` / LibreOffice;
- opens / shares files via `gui.toga_backend.share.open_file` which
  delegates to `toga.App.open_url` (mobile share sheet / system intent);
- lazy-imports `pandas` + `matplotlib` via
  `gui.toga_backend.resources.lazy_import` to keep cold-start fast on
  low-end Android devices.

## Signing / notarization

Desktop signing is unchanged:

- Windows Authenticode cert + timestamp URL via the existing
  `release.yml` secrets.
- macOS Developer ID via `APPLE_DEV_ID_APP` + notarytool.

Mobile signing:

- **iOS**: Apple Developer account + provisioning profile. Briefcase
  picks up certificates from the macOS keychain; CI uses
  `fastlane match` or the equivalent.
- **Android**: release keystore (PKCS#12) uploaded as a CI secret plus
  the four env vars listed above. `briefcase package android` invokes
  the gradle sign + zipalign chain automatically.

## Testing cold-start

Use `adb shell am start -W com.wysscenter.dbsannotator/org.beeware.android.MainActivity`
to measure activity creation time on a low-end Android test device
(Pixel 3a or lower). Target is < 2 s to first interactive frame; if
you regress past 3 s, audit for new synchronous imports in
`gui.toga_backend.app.startup`.
