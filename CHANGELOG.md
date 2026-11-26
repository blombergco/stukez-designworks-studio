# Changelog

All notable changes to StukeZ Designworks Studio. Versions follow `major.minor.patch`: a patch fixes something, a minor
adds something, a major changes how your data is stored. The newest release is the top entry; the text under it is what
the update dialog shows.

## 1.3.2

- New workspaces come with 236 synthetic test projects (random names and palettes, no real design data) besides the six examples, so you can try the grid with many projects and make your own colour combinations. They are plain palettes: no week status or other details.

## 1.3.1

- The Projects grid is smooth from the moment the program starts: every project card is drawn once while the splash shows ("Preparing project cards"), then scrolling only copies the finished pictures.
- Hover and selection are drawn on top of the cards, so moving the mouse no longer redraws the whole card.
- Card pictures are kept within a memory budget based on your RAM (32 to 128 MB), so weaker PCs use less memory.
- Fixed a build problem where the installer could not find its starter files.

## 1.3.0

- The Workshop tab *Sponsors and outlines* is gone: the colours of the sponsors and their outlines are set on New project (with a live preview) and, per logo, on *Place on car*.
- A little motion: a new palette sweeps across the car in the preview (the cut of the livery slides in from the front), pages fade in, and the logo in the rail shines once at start and when you point at it. `KAIZEN_NOANIM=1` turns all of it off.
- Tidied up: the *Solid tribals* choice of the Car paint switch is gone (Gradient and Solid base are enough), the wheel boxes and the vector wheels went with the cars that needed them, and the Illustrator template menu only lists the views the preview car has.
- **Three themes**: Red and black (the studio's own look), Blue and black (blue-black with electric blue and white accents) and Carbon and yellow (a carbon-fibre weave with racing yellow). Pick one in the box at the top right, or press `Ctrl+T` for the next; the choice is remembered. Everything follows it: buttons, tabs, the rail, the stage behind the cars, the notes and the logo.
- **A new logo**: an angular S and Z on a plate cut at 45 degrees and split along the same line as the livery gradient. It takes the colours of the theme, and it is the program icon, the mark in the rail and the picture on the **start screen** that shows while the program loads.
- **Compare…** on the Projects page puts two projects on the preview car, one above the other, with their seven colours; *Swap* turns them round.
- **Surprise me** (New project) makes a new random palette and also picks a random preview car; **Shuffle** (Place on car) throws the logos and tribals into new places, sizes and sponsor colours for quick ideas, and can be undone.
- Solid-colour cars: a **Car paint** switch (Gradient, Solid base) on the Projects, New project and Workshop pages changes every preview (cards, detail view, On car, Illustrator template) between the livery cut and the flat base colour. One choice for the whole program, remembered between runs. The Gradients page always shows its cut.
- Outlines can be gradients too: every outline slot in New project has a 2-colour gradient box, the Gradients page can send its pair to the three outline slots, and Logo outlines can paint the contour as a left-to-right gradient. Saved projects keep a gradient outline as two hex codes (the vault's `projectkit` now allows it; older projects are unchanged), and the placement preview paints sponsor outlines in the gradient.
- **Place on car** (Workshop, first tab) replaces the fixed sponsor boxes as the way to try a livery: import sponsor logos and tribals (PNG, SVG, WebP, JPG; drop files on the car, take logos from the logo library, or type a name when there is no logo), drag them anywhere on the car, scale them with the corners, turn them with the round handle, nudge with the arrow keys, mirror, change opacity, reorder. Each one can keep its own colours or take Sponsor A, Sponsor B, the tribal or base colour, or any custom colour or 2-colour gradient, with an optional outline (from the palette or custom). Side and top views, undo and redo, snapping to the middle of the car, the sponsor zones as an optional guide. Boards are saved automatically in `Project Library/Boards/` (the imported files are copied next to them), and *Use this board on all car previews* shows the board, recoloured with each project's palette, on the cards, the detail view and New project instead of the small plates. *Save image* and *Copy image* export the car with its logos.
- Only two built-in cars are left, the S13 Silvia and the S15 Origin Raijin kit; the others did not come out well enough. Your own cars on the Cars page are unaffected. The wheel boxes next to Preview car only show for a car that has vector wheels.
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
