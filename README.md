# No Floating Family in Main Menu

Removes the household Sims from the main menu, so a custom menu backdrop is
just the backdrop.

By GhostWorldTourist.

## The problem

The main menu draws your active household on top of the menu art. With EA's own
backdrop they are posed to fit it. Install a custom main menu and nothing tells
the household about it, so the family ends up standing in mid-air in front of
somebody else's living room, lit differently and grounded on a floor that is not
there.

Nothing is broken and nothing errors. It just looks wrong, and there is no
setting for it.

## How it works

The household is framed by one of ten camera rigs, chosen by how many Sims are
in it:

    auHousehold_MainMenu_Close        Medium        Max
    auHousehold_MainMenu_Close_Odd    Medium_Odd    Max_Odd
    auHousehold_MainMenu_Horses_Few   Horses_Few_Odd
    auHousehold_MainMenu_Horses_Many  Horses_Many_Odd

They are `Client_CASThumbnailCamera` rigs — the same machinery that renders a
CAS thumbnail. **That is the whole reason this mod can exist**: the Sims are
rendered in their own pass and composited over the menu, so moving their camera
moves them and touches nothing else. The backdrop is drawn by something this mod
never goes near.

This mod ships all ten rigs with one field changed. `TargetPosition` becomes the
camera position mirrored through itself — `2 x camera - target` — so each rig
looks along exactly the reverse of its original aim, with the Sims behind it.
Nothing renders.

Mirroring rather than a fixed "look over there" point is deliberate: the ten rigs
sit at different heights, distances and horizontal offsets, and the reverse of a
rig's own aim is the one direction guaranteed to point away from whatever it was
framing. A single hard-coded target would have had to be checked ten times and
would break on any rig EA adds later.

## The part that is not obvious

**These are not XML tuning.** `camera` is client-side — consumed by the C++
client and never registered in `sims4.resources.Types`, which is why 1,920 camera
instances sit unmapped in a full index of the game. Each rig ships as a
**SimData** resource, type `0x545AC67A`, group `0x00496642`, and its three
columns are:

| column | type | offset |
| --- | --- | --- |
| `CameraPosition` | Vector3 | 0 |
| `TargetPosition` | Vector3 | 12 |
| `CameraFOV` | **Int32** | 24 |

FOV being an integer is worth writing down, because reading those four bytes as
a float returns `0.0` rather than an error — a plausible value that is silently
wrong. The real values run 10 to 16 and differ per rig.

The build takes EA's own resource and rewrites twelve bytes rather than authoring
a SimData from scratch, so the schema, the FOV and the resource size are
byte-identical to what the client already reads.

## What is verified, and what is not

**Verified**, by reading the built package back and diffing every resource
against EA's original: all ten present under the right type and group, camera
position unchanged, FOV unchanged, size unchanged, schema preserved, target
mirrored to within 1e-4, and the aim confirmed to point away from the Sims.

**Not verified: how it looks in game.** The geometry says the Sims are behind
every camera, but this has not been launched yet. If a rig turns out to have a
back-facing quirk, the fix is in `build.py` and takes a minute.

## Install

Drop `GhostWorldTourist_NoFloatingFamilyInMainMenu.package` in `Mods\`, one
folder deep at most. No script mod, so nothing to enable.

To undo it, delete the file — nothing is patched in place.

## Rebuild

    py build.py

Reads the current cameras out of the installed game, so it stays correct across
patches. Re-run it after an update if the menu framing ever changes.
