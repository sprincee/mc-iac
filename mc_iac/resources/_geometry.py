"""
_geometry.py

Shared structure-generation helpers used by multiple resource types.
All functions return lists of Minecraft command strings.

Coordinate conventions (project-wide):
  +x = east, -x = west, +z = south, -z = north
  Anchor position = the minimum-x / minimum-z corner (north-west corner).
  Structures extend east (+x) and south (+z) from the anchor.
"""


def slab_for(stair_material: str) -> str:
    """Derive a slab block id from a stairs id, e.g. dark_oak_stairs -> dark_oak_slab."""
    if stair_material.endswith("_stairs"):
        return stair_material.replace("_stairs", "_slab")
    return stair_material


def clear_volume(x1, y1, z1, x2, y2, z2) -> list[str]:
    """Fill a volume with air. Coordinates are inclusive."""
    return [f"fill {x1} {y1} {z1} {x2} {y2} {z2} minecraft:air"]


def hollow_walls(x, y, z, width, depth, height, material) -> list[str]:
    """
    Four walls of a rectangular building. Floor NOT included.
    x, y, z = anchor (NW corner, floor level). Walls occupy y+1 .. y+height.
    """
    x2 = x + width - 1
    z2 = z + depth - 1
    return [
        f"fill {x} {y+1} {z} {x2} {y+height} {z} minecraft:{material}",       # north wall
        f"fill {x} {y+1} {z2} {x2} {y+height} {z2} minecraft:{material}",     # south wall
        f"fill {x} {y+1} {z} {x} {y+height} {z2} minecraft:{material}",       # west wall
        f"fill {x2} {y+1} {z} {x2} {y+height} {z2} minecraft:{material}",     # east wall
    ]


def corner_frames(x, y, z, width, depth, height, material) -> list[str]:
    """Vertical log columns at the four corners, y+1 .. y+height."""
    x2 = x + width - 1
    z2 = z + depth - 1
    return [
        f"fill {x} {y+1} {z} {x} {y+height} {z} minecraft:{material}",
        f"fill {x2} {y+1} {z} {x2} {y+height} {z} minecraft:{material}",
        f"fill {x} {y+1} {z2} {x} {y+height} {z2} minecraft:{material}",
        f"fill {x2} {y+1} {z2} {x2} {y+height} {z2} minecraft:{material}",
    ]


def gable_roof(x, z, width, depth, y_base, stair_material,
               gable_material=None, overhang=1) -> list[str]:
    """
    Pitched gable roof with the ridge running along the x (east-west) axis.
    Slopes face north and south. Stair rows step inward and upward from
    both the north and south edges until they meet at the ridge.

    y_base = the y level of the FIRST (lowest) roof row.
    gable_material: if given, fills the triangular end-walls (at the
    anchor's west and east wall x-positions) under the roof.

    Returns fill commands.
    """
    cmds = []
    rx1 = x - overhang
    rx2 = x + width - 1 + overhang
    rz1 = z - overhang
    rz2 = z + depth - 1 + overhang

    k = 0
    while True:
        zn = rz1 + k   # north-side row for this level
        zs = rz2 - k   # south-side row for this level
        yk = y_base + k

        if zn > zs:
            break

        if zn == zs:
            # Odd number of rows: single ridge row, cap with slabs
            cmds.append(
                f"fill {rx1} {yk} {zn} {rx2} {yk} {zn} "
                f"minecraft:{slab_for(stair_material)}[type=bottom]"
            )
            break

        # North slope row ascends toward the south -> stairs face south
        cmds.append(
            f"fill {rx1} {yk} {zn} {rx2} {yk} {zn} "
            f"minecraft:{stair_material}[facing=south,half=bottom]"
        )
        # South slope row ascends toward the north -> stairs face north
        cmds.append(
            f"fill {rx1} {yk} {zs} {rx2} {yk} {zs} "
            f"minecraft:{stair_material}[facing=north,half=bottom]"
        )

        # Gable end-wall infill at the building's west/east wall positions
        if gable_material is not None and zn + 1 <= zs - 1:
            wx1 = x
            wx2 = x + width - 1
            cmds.append(
                f"fill {wx1} {yk} {zn+1} {wx1} {yk} {zs-1} minecraft:{gable_material}"
            )
            cmds.append(
                f"fill {wx2} {yk} {zn+1} {wx2} {yk} {zs-1} minecraft:{gable_material}"
            )

        k += 1

    return cmds


def gable_roof_height(depth, overhang=1) -> int:
    """Number of vertical levels a gable roof adds above its y_base."""
    rows = depth + 2 * overhang
    return (rows + 1) // 2


def pyramid_roof(x, z, width, depth, y_base, stair_material,
                 cap_material, overhang=1) -> list[str]:
    """
    Pyramid roof (rings stepping inward on all four sides), for towers.
    Assumes a roughly square footprint.
    """
    cmds = []
    rx1 = x - overhang
    rx2 = x + width - 1 + overhang
    rz1 = z - overhang
    rz2 = z + depth - 1 + overhang

    k = 0
    while True:
        x1, x2 = rx1 + k, rx2 - k
        z1, z2 = rz1 + k, rz2 - k
        yk = y_base + k

        if x1 > x2 or z1 > z2:
            break

        if x2 - x1 <= 1 or z2 - z1 <= 1:
            # Degenerate ring: cap it
            cmds.append(f"fill {x1} {yk} {z1} {x2} {yk} {z2} minecraft:{cap_material}")
            break

        # North and south rows (full ring width)
        cmds.append(
            f"fill {x1} {yk} {z1} {x2} {yk} {z1} "
            f"minecraft:{stair_material}[facing=south,half=bottom]"
        )
        cmds.append(
            f"fill {x1} {yk} {z2} {x2} {yk} {z2} "
            f"minecraft:{stair_material}[facing=north,half=bottom]"
        )
        # West and east columns (excluding the corners already placed)
        if z1 + 1 <= z2 - 1:
            cmds.append(
                f"fill {x1} {yk} {z1+1} {x1} {yk} {z2-1} "
                f"minecraft:{stair_material}[facing=east,half=bottom]"
            )
            cmds.append(
                f"fill {x2} {yk} {z1+1} {x2} {yk} {z2-1} "
                f"minecraft:{stair_material}[facing=west,half=bottom]"
            )

        k += 1

    return cmds
