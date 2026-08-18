"""No Floating Family in Main Menu - build script.

The main menu draws your household over the menu backdrop. With a custom main
menu installed the two do not agree, and the family ends up standing in mid-air
in front of somebody else's living room.

How this works
--------------
The household on the menu is rendered through its own camera, one of ten
`auHousehold_MainMenu_*` rigs picked by household size (Close / Medium / Max,
each with an _Odd variant, plus three for horses). They are `Client_CASThumbnail`
cameras - the same machinery that renders a CAS thumbnail - so they frame the
Sims in a separate pass and have nothing to do with the backdrop behind them.
Point them somewhere else and the Sims stop being drawn; the menu art is
untouched.

They are NOT XML tuning. `camera` is client-side, consumed by the C++ client and
never registered in `sims4.resources.Types`, and each rig ships as a **SimData**
resource (type 0x545AC67A, group 0x00496642) holding three columns:

    CameraPosition   Vector3   offset 0
    TargetPosition   Vector3   offset 12
    CameraFOV        Int32     offset 24     <- an int, not a float

Rather than author a SimData from scratch, this takes EA's own resource and
rewrites twelve bytes: TargetPosition becomes the camera position mirrored
through itself, `2*camera - target`, so each rig looks along exactly the reverse
of its original aim. The Sims are then behind the camera. Mirroring is used
instead of a fixed "look over there" point because the ten rigs sit at different
heights and offsets, and the reverse of each one's own aim is guaranteed to be
away from what it was framing.

Nothing else in the resource is touched: same schema, same FOV, same instance
ids, so the client reads exactly the structure it expects.

Author: GhostWorldTourist
"""
import os, struct, sqlite3, sys

sys.path.insert(0, os.path.join(os.environ['LOCALAPPDATA'], 'sulskill', 'ts4-knowledge', 'lib'))
sys.path.insert(0, os.path.join(os.path.expanduser('~'), 'repos', 'sulskill', 'sulskill-modbuild', 'scripts'))
import dbpf_index, simdata, dbpf

GAME    = r'C:\Games\The Sims 4'
SOURCE  = os.path.join(GAME, r'Data\Simulation\SimulationDeltaBuild0.package')
DB      = os.path.join(os.environ['LOCALAPPDATA'], 'sulskill', 'ts4-knowledge', 'out', 'ts4.db')
SIMDATA = 0x545AC67A
GROUP   = 0x00496642
HERE    = os.path.dirname(os.path.abspath(__file__))
OUT     = os.path.join(HERE, 'GhostWorldTourist_NoFloatingFamilyInMainMenu.package')


def cameras():
    db = sqlite3.connect(DB)
    return {int(r[0]): r[1] for r in db.execute(
        "SELECT DISTINCT id, name FROM instances "
        "WHERE name LIKE 'auHousehold_MainMenu%'")}


def main():
    names = cameras()
    print('main-menu camera rigs: %d' % len(names))
    entries = {i: (off, sz, comp)
               for (t, g, i, off, sz, comp) in dbpf_index.index(SOURCE)
               if t == SIMDATA and i in names}
    missing = set(names) - set(entries)
    if missing:
        print('NOT FOUND in %s: %s' % (SOURCE, missing), file=sys.stderr)
        return 2

    resources = []
    for iid in sorted(entries, key=lambda k: names[k]):
        data = bytearray(list(dbpf_index.fetch(SOURCE, [entries[iid]]))[0])
        table = simdata.parse(bytes(data))['tables'][0]
        rp = table['row_pos']
        cam = struct.unpack_from('<3f', data, rp)
        tgt = struct.unpack_from('<3f', data, rp + 12)
        new = tuple(2.0 * c - t for c, t in zip(cam, tgt))
        struct.pack_into('<3f', data, rp + 12, *new)
        resources.append((SIMDATA, GROUP, iid, bytes(data)))
        print('  %-38s aim (%.2f, %.2f, %.2f) -> (%.2f, %.2f, %.2f)'
              % (names[iid], *tgt, *new))

    n, size = dbpf.write(OUT, resources)
    print('\nwrote %s\n  %d resources, %d bytes' % (OUT, n, size))
    return 0


if __name__ == '__main__':
    sys.exit(main())
