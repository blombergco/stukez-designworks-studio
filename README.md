# StukeZ Designworks Studio

A Windows design studio for drift liveries: generate and edit colour palettes, see them on your own cars, build gradients and logo outlines, keep a sponsor database, and export everything for Illustrator and Substance Painter. Everything you make is stored as plain Markdown notes in a folder you own (a *workspace*, which also opens in Obsidian).

**Download:** the newest `...-Setup.exe` on the [Releases](../../releases) page. It installs for your user, no administrator rights needed, and updates itself from here.

The rest of this page is for people who work on the program, or keep their own vault.

## Use it

Double-click `StukeZ Designworks Studio.exe` in this folder. It finds the vault by looking at the folders above itself; if you move it, it asks once for the Kaizen Cave folder and remembers it. `F5` reloads after you changed notes in Obsidian, `Ctrl+1` to `Ctrl+5` switch page.

| Page | What it does |
|---|---|
| **Projects** | Card grid of every project (livery preview, 4 colour chips), search and filters (mood, platform), detail view with all 7 hex codes (click to copy), the project note, Build sheet, Detail kit, Patterns and the prompts that carry the palette. Exports: palette card PNG, `.ase` swatches, all hex to clipboard, open note, show folder. |
| **New project** | Type a name or press *Suggest name*; pick moods and a colour scheme and press *Generate* (`Ctrl+G`), or edit every colour by hand (lock a colour to keep it while generating). Live livery preview, rule check (gradients of exactly 2 colours, single-colour outlines, contrast warning). *Save* writes `NNN Name/` with the project note and patterns note, an `.ase` file in `Swatches/`, and rebuilds the Projects index. |
| **Cars** | Your car library: Substance Painter captures of the cars, **side view and top view** for now. *Add a car…* takes one car (point at its folder and the names Side / Top are recognised); *Import a folder of cars…* scans a whole folder tree, lists every car it finds (a car per folder, or per name such as `S13 side.png` + `S13 top.png`; a folder full of variants counts as one car) and imports the ticked ones. The captures are cropped and stored at full resolution as WebP in `Project Library/Car Templates/<Car>/` with a `car.json`; the originals are never touched. **Flip the car** mirrors the side view (or turns the top view 180°) with its zones and direction. Each view shows the 12 sponsor zones: drag to move, drag the dot to resize, right-click to add or delete. **The placement belongs to the car** (stored in its `car.json`, saved on every change, shown as “✓ placed” in the list), so every car model keeps its own sponsor placement; *Copy the placement from another car…* starts a new car from one you already placed (mirrored if it faces the other way). Pick a project in the box under the picture and its real sponsor logos show up in the zones while you place them. *Export Illustrator template…* writes the capture on its original canvas (same size as your screenshot), a numbered zone-guide PNG and an SVG with the layers Car, Zones and Palette. |
| **Prompts** | All 445 Gemini prompts by category. Choose a colour version: greyscale master, the palette from the New project page, any project, or the ready-made options stored in the note. *Copy prompt* puts it on the clipboard. |
| **Sponsors** | The Drift Sponsor Database filtered by chassis and engine (same matching as `query.py`), category, region and text. Colour-coded fit (fits your build / universal / check fitment), brand note on the right. *Copy list* or *Save as vault note* (to `Sponsor Lists/`). |
| **Guides** | Glossaries, style guide, placement and paint guides, year plan, logo notes. Wikilinks work; links to a project open it on the Projects page. |
| **Workshop** | Tools for making parts of a livery. **Gradients**: pick a rear and a front colour (suggestions: analogous, complement, split, triad, lighter, darker), set the cut (angle, centre, how much of the car it covers; the studio standard is 45°, centred, half the car), see it on your car, keep favourites in `Project Library/Gradients/` and export `.ase`; *Use in New project* sends the pair to the base, tribal or a sponsor slot. **Logo outlines**: one single-colour contour around a sponsor logo (thickness, gap, join letters, round corners, colour from the logo or a project), saved as outlined PNG, outline only, a cut plate and a layered SVG; a whole folder at once is possible. Drop an image on the preview to open it. |

## Your own cars

The **Preview car** box (top right) switches every preview (cards, detail view, New project) from the generic coupe to one of your cars, with the palette's base gradient, tribals and sponsor plates painted on the capture. The project page gets an **On car** tab: all four views with the real sponsor logos placed in the zones of that car (same logo masters and text stand-ins as the generic Placement preview), plus a PNG export, and an **Illustrator template** button that exports a view in the project's colours.

For the best result capture a **clean grey base**: every panel one mid-grey, glass left white, no livery. The app then keeps the shading, panel lines and highlights of the capture and paints the livery under them, and draws the white glass dark (the *White areas are windows* box turns that off, which a white car needs). A capture that already carries a livery still works, but only its silhouette and fine panel lines are used, so the old paint never shows. The side view's front is detected (it is the end with the lower hood line); the top view's front is a setting, default *at the bottom* like your ER34 capture. Both are editable per car.

## What a saved project contains

A project created in the app is complete, like the first 236: project note with Design vocabulary (colour scheme, hue families, value structure and inferred finish, classified from the hex codes), patterns note, `.ase` swatches, **Detail kit** (8 of the 81 universal details picked for the project's moods, with its hex codes in every prompt), **Build sheet** (Substance 3D Painter recipe for the inferred finish, 12-zone sponsor kit and the 36-slot dense layout) and a **placement preview** image. The *Also build…* box next to *Save* controls this; it takes about a second plus the preview.

`stukez_studio/builder.py` is a port of the vault's archived generators (`build_kits.py`, `build_sheets.py`, `build_jp.py`), checked by regenerating project 001: the build sheet template came out identical. The rotation counters (which details and brands are already used a lot) are read from the existing notes, so a new project continues the rotation instead of repeating the same sponsors. It uses the vault's own data modules and `Tools/placement_preview.py` (real logo masters from the folder on `D:` where they exist, text stand-ins otherwise).

Older projects or ones made before this feature show **Build missing parts** on the Projects page, which creates whatever is absent. It never overwrites an existing kit or sheet. Not covered: the generated list of prompts under *Motifs* (run `colouroptions.py` from Obsidian's side if you want it; the Prompts page can recolour any prompt with any project anyway), the *Palette of the day* calendar and the `All projects.ase` master file.

## Run from source / rebuild the exe

```
py -3 run_studio.py
powershell -File build_exe.ps1
```

Needs `py -3` with `PySide6`, `markdown`, `pillow`, `pyinstaller` (the build script installs them). The exe is one file of roughly 60 MB; it starts in a few seconds because it unpacks itself. `build/`, `dist/` and the exe are git-ignored.

## Layout

```
stukez_studio/backend.py        vault access, prompts, sponsors, note rendering, .ase writer
stukez_studio/palette.py        colour maths, mood-based generator, name generator, rule check
stukez_studio/builder.py        design vocabulary, detail kit, build sheet + sponsor kit, placement preview
stukez_studio/kit_rules.py      mood / style / theme / finish rules for the detail kit (copied from the vault)
stukez_studio/cars.py           car library: import and crop captures, car.json, default sponsor zones
stukez_studio/carrender.py      paints a palette on a capture (flat livery x shading of the capture); the livery is one 45° gradient over half the car: base behind the middle of the door, tribal colour in front
stukez_studio/oncar.py          placement image on a real car with the sponsor logos
stukez_studio/templates.py      Illustrator template export (PNG + zone guides + layered SVG)
stukez_studio/render.py         livery car, palette card, PNG export
stukez_studio/theme.py          the look: tyre black, signal red and paper white in DIN (Bahnschrift), cut at 45°; all colours and the stylesheet
stukez_studio/rail.py           the navigation rail: wordmark, drawn page icons, racing stripe
stukez_studio/widgets.py        the cut Studio buttons and headings, note viewer, colour tiles, preview stage, progress helper
stukez_studio/gradients.py       gradient suggestions, favourites file, .ase export (no Qt)
stukez_studio/outlines.py       logo outline engine (numpy and Pillow, no Qt)
stukez_studio/backup.py         back up the vault: commit and push to GitHub
stukez_studio/export.py         project package (ZIP)
stukez_studio/builtin/s13-silvia/  the built-in preview car (picture, paint mask, zones); made with make_default_car.py from an illustration
stukez_studio/page_*.py         the pages (Workshop has two tabs: gradients, logo outlines)
stukez_studio/main.py           main window, vault lookup
```

The UI is in English to match the vault's terms (Tribals, Sponsor A/B, Build sheet).

## Backup

`File > Back up to GitHub…` (`Ctrl+B`) commits everything that changed in the vault and pushes it to the `origin` remote. It only adds a new commit; nothing is rewritten or deleted. Set the remote up once with `gh repo create` (see the project notes). `Studier/`, `Gemini Prompt/` and `CV/` are kept out of the backup on purpose (`.gitignore`).

`Projects > Export package (ZIP)` saves a project's notes, swatches, placement preview and palette card in one file.

## Installing and updating (for other people)

Run `StukeZ-Designworks-Studio-<version>-Setup.exe`. It installs for the current user (no administrator rights) and adds a Start menu entry. On the first start a welcome dialog makes a **workspace** (default `Documents\StukeZ Designworks Studio`) with six example palettes, or opens a vault you already have. Your work lives in the workspace, so uninstalling or updating the program never touches it.

The program checks for a newer version a few seconds after it starts (switch off under Help > Check for updates at startup) and under Help > Check for updates. It downloads the installer from the GitHub release, checks its SHA-256, and runs it; your workspace stays as it is. Windows may show "unknown publisher" until the installer is code signed.

A new workspace starts with no logos, sponsor brands, prompts or cars: add your own (cars on the Cars page, logo files in `Project Library/Sponsor Logo Library/Logo masters`, named `Brand__black__4096px.png`).

## Making a release (for the author)

1. Change what you want, add it to `CHANGELOG.md` under a new `## x.y.z` heading, and set `__version__` in `stukez_studio/__init__.py`.
2. If the vault tools changed, or the version changed: `py -3 make_starter.py` (rebuilds `starter/` and `legal/`) and commit the result.
3. Locally: `powershell -File build_installer.ps1` makes `dist\installer\...-Setup.exe` and its `.sha256` (needs Inno Setup 6: `winget install JRSoftware.InnoSetup`).
4. Publish: `git tag vx.y.z && git push origin vx.y.z`. The workflow in `.github/workflows/release.yml` builds, smoke-tests in a fresh workspace and attaches the installer and checksum to a GitHub Release. Everyone's program then offers the update.

The repository that holds the releases is set in `stukez_studio/updates.py` (`REPO`). Releases must be public for other people's programs to see them.
