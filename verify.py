"""Check the shipped package without needing the game installed.

build.py reads the cameras out of your Sims 4 install, so it cannot run in CI.
This can: everything it asserts is derived from the package itself, so a bad
build cannot reach a release even though the build machine is the only one with
the game on it.

What it proves:
  - exactly the ten main-menu camera rigs are present
  - each is SimData under the type and group the client reads
  - each still declares the Client_CASThumbnailCamera schema, so the client
    finds the layout it expects
  - each camera now aims AWAY from the Sims - the actual point of the mod,
    checked as a sign test rather than by trusting the numbers that were written

Exit 0 if the package is good, 1 if not.
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, 'GhostWorldTourist_NoFloatingFamilyInMainMenu.package')
SIMDATA = 0x545AC67A
GROUP = 0x00496642
EXPECT = 10


def resources(path):
    """(type, group, instance, decompressed bytes) per entry. Index-only DBPF."""
    with open(path, 'rb') as f:
        data = f.read()
    if data[:4] != b'DBPF':
        raise ValueError('not a DBPF package')
    count = struct.unpack_from('<I', data, 0x24)[0]
    ix_size = struct.unpack_from('<I', data, 0x2C)[0]
    ix_off = struct.unpack_from('<Q', data, 0x40)[0]
    ix = data[ix_off:ix_off + ix_size]
    struct.unpack_from('<I', ix, 0)          # flags word; this writer sets none
    p = 4
    for _ in range(count):
        t, g, ihi, ilo, off, csize, usize, comp, _u = struct.unpack_from('<IIIIIIIHH', ix, p)
        p += 32
        blob = data[off:off + (csize & 0x7FFFFFFF)]
        yield t, g, (ihi << 32) | ilo, (zlib.decompress(blob) if comp == 0x5A42 else blob)


def row_offsets(blob):
    """(row_pos, schema name) from a SimData resource."""
    def rel(pos):
        v = struct.unpack_from('<i', blob, pos)[0]
        return None if v in (-1, -0x80000000) else pos + v

    def cstr(pos):
        return blob[pos:blob.index(b'\x00', pos)].decode('utf-8', 'replace')

    schema_pos = rel(16)
    table_pos = rel(8)
    name = cstr(rel(schema_pos))
    return rel(table_pos + 20), name, cstr(rel(table_pos))


def main():
    if not os.path.isfile(PKG):
        print('missing %s' % PKG, file=sys.stderr)
        return 1
    seen, bad = [], []
    for t, g, i, blob in resources(PKG):
        row, schema, table = row_offsets(blob)
        cam = struct.unpack_from('<3f', blob, row)
        tgt = struct.unpack_from('<3f', blob, row + 12)
        # The Sims stand at the origin. If the camera still aims towards it, the
        # mod does nothing - so test the sign of the dot product rather than the
        # coordinates, which makes this independent of each rig's geometry.
        aim = [a - b for a, b in zip(tgt, cam)]
        to_sims = [0.0 - c for c in cam]
        away = sum(a * b for a, b in zip(aim, to_sims)) < 0
        problems = []
        if t != SIMDATA:
            problems.append('type 0x%08X' % t)
        if g != GROUP:
            problems.append('group 0x%08X' % g)
        if schema != 'Client_CASThumbnailCamera':
            problems.append('schema %r' % schema)
        if not table.startswith('auHousehold_MainMenu'):
            problems.append('unexpected rig %r' % table)
        if not away:
            problems.append('STILL AIMS AT THE SIMS')
        seen.append(table)
        print('  %-38s %s' % (table, 'ok' if not problems else 'BAD: ' + ', '.join(problems)))
        if problems:
            bad.append(table)

    print()
    if len(seen) != EXPECT:
        print('expected %d camera rigs, found %d' % (EXPECT, len(seen)), file=sys.stderr)
        return 1
    if bad:
        print('%d rig(s) bad' % len(bad), file=sys.stderr)
        return 1
    print('%d rigs, all aiming away. Package is good.' % len(seen))
    return 0


if __name__ == '__main__':
    sys.exit(main())
