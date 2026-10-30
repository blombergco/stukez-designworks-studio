# Changelog

All notable changes to StukeZ Designworks Studio. Versions follow `major.minor.patch`: a patch fixes something, a minor
adds something, a major changes how your data is stored. The newest release is the top entry; the text under it is what
the update dialog shows.

## Unreleased

- Solid-colour cars: a **Car paint** switch (Gradient, Solid base, Solid tribals) on the Projects, New project and Workshop pages changes every preview (cards, detail view, On car, Illustrator template) between the livery cut and one flat colour. One choice for the whole program, remembered between runs. The Gradients page always shows its cut.
- Outlines can be gradients too: every outline slot in New project has a 2-colour gradient box, the Gradients page can send its pair to the three outline slots, and Logo outlines can paint the contour as a left-to-right gradient. Saved projects keep a gradient outline as two hex codes (the vault's `projectkit` now allows it; older projects are unchanged), and the placement preview paints sponsor outlines in the gradient.
- Ten more built-in cars, cut out of the illustrations in the same way as the S13 Silvia, so only the paint takes the livery and windows, wheels and lights keep their colours: S13 B-style, 180SX Origin kit, S14 D-Max kit, S15 Origin Raijin kit, ER34 Uras bodykit, JZX90 BN Sport, Galant, E36 Coupe and S160 Junction Produce (twelve built-in cars in all). `make_builtin_illustrations.py` rebuilds them.
- Windows on the cars that come with a plain grey base (S13 Origin kit, S15 Raiji kit) are drawn as tinted glass with a soft reflection and smooth edges instead of flat black blocks, and the sponsor zones of the built-in cars sit clear of the wheels.
- Workshop has a new tab, **Sponsors and outlines**: change the colour or gradient of Sponsor A, Sponsor B and their outlines on big plates on the car, start from the New project page or any project, fix outline contrast in one click, and send the result to New project.
- A **How to** page (Ctrl+8) explains the program in a few short topics.
- Two more built-in cars: the S13 Origin kit and the S15 Raiji kit (side and top views). The S13's colours were neutralised, so every palette paints it cleanly.
- Vector wheels for those cars: a Volk TE37 (6 spokes) and a Work VS-KF (5 spokes), drawn in the program so they stay sharp at any size. Pick the wheel and its colour (bronze, black, white, silver, gunmetal, gold) with the two new boxes next to Preview car. The S13 comes with TE37 in bronze and the S15 with VS-KF in gunmetal.

## 1.2.2

- The program is marked as beta while it is being tested: a "beta" tag in the sidebar, "(beta)" in the window title, the version shown as "x.y.z beta" in About and the update dialogs, and "beta" in the installer's name (for example `StukeZ-Designworks-Studio-1.2.2-beta-Setup.exe`). Updates from earlier versions work as before.

## 1.2.1

- The plain coupe is gone: the Preview car box lists the built-in S13 Silvia and your own cars.

## 1.2.0

- A built-in car, an S13 Silvia, is now the default preview car instead of the plain coupe. Only its paint takes the palette; windows, wheels and lights keep their own colours. The Preview car box still lists the plain coupe and your own cars.
- Projects shows the bare car: the sponsor plates are gone from the project cards, the detail picture and the exported palette card. New project still shows small plates, because that is where the sponsor colours are chosen.

## 1.1.1

- The sponsor plates in the previews (project cards, project detail, New project) are much smaller, so the car and its colours show. The Illustrator export keeps the full-size zones.

## 1.1.0

- New name and look: DIN type, every button, card and colour tile cut at 45 degrees, a new navigation rail and a garage-floor stage behind the cars.
- The livery preview is one 45 degree gradient over half the car (rear colour behind the door, front colour ahead of it).
- Workshop: a gradient generator (colour suggestions, the cut's angle, centre and size, favourites, `.ase` export) and a logo outline generator (one single-colour contour, whole folders at once, layered SVG).
- Export package (ZIP) for a project, and File > Back up to GitHub for people who keep their workspace in git.
- First start: a welcome dialog makes a workspace for you, with six example palettes, or opens an existing vault.
- Help > Check for updates, and an automatic check at startup that you can switch off.
- Runs in a fresh workspace without the author's logo library, sponsor database or prompt library; steps that need them say what is missing.

## 1.0.0

- First version: projects, new project generator, cars, prompts, sponsors and guides on top of the vault.
