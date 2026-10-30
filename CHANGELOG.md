# Changelog

All notable changes to StukeZ Designworks Studio. Versions follow `major.minor.patch`: a patch fixes something, a minor
adds something, a major changes how your data is stored. The newest release is the top entry; the text under it is what
the update dialog shows.

## Unreleased

- Solid-colour cars: a **Car paint** switch (Gradient, Solid base, Solid tribals) on the Projects, New project and Workshop pages changes every preview (cards, detail view, On car, Illustrator template) between the livery cut and one flat colour. One choice for the whole program, remembered between runs. The Gradients page always shows its cut.
- Outlines can be gradients too: every outline slot in New project has a 2-colour gradient box, the Gradients page can send its pair to the three outline slots, and Logo outlines can paint the contour as a left-to-right gradient. Saved projects keep a gradient outline as two hex codes (the vault's `projectkit` now allows it; older projects are unchanged), and the placement preview paints sponsor outlines in the gradient.
- **Place on car** (Workshop, first tab) replaces the fixed sponsor boxes as the way to try a livery: import sponsor logos and tribals (PNG, SVG, WebP, JPG; drop files on the car, take logos from the logo library, or type a name when there is no logo), drag them anywhere on the car, scale them with the corners, turn them with the round handle, nudge with the arrow keys, mirror, change opacity, reorder. Each one can keep its own colours or take Sponsor A, Sponsor B, the tribal or base colour, or any custom colour or 2-colour gradient, with an optional outline (from the palette or custom). Side and top views, undo and redo, snapping to the middle of the car, the sponsor zones as an optional guide. Boards are saved automatically in `Project Library/Boards/` (the imported files are copied next to them), and *Use this board on all car previews* shows the board, recoloured with each project's palette, on the cards, the detail view and New project instead of the small plates. *Save image* and *Copy image* export the car with its logos.
- Only two built-in cars are left, the S13 Silvia and the S15 Origin Raijin kit; the others did not come out well enough. Your own cars on the Cars page are unaffected. The wheel boxes next to Preview car only show for a car that has vector wheels.
- Workshop has a new tab, **Sponsors and outlines**: change the colour or gradient of Sponsor A, Sponsor B and their outlines on big plates on the car, start from the New project page or any project, fix outline contrast in one click, and send the result to New project.
- A **How to** page (Ctrl+8) explains the program in a few short topics.

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
