import hashlib
from mc_iac.resources.base import Resource
from mc_iac.resources._geometry import (
    clear_volume, hollow_walls, corner_frames, gable_roof, gable_roof_height,
)

PEN_SPAN = 4   # pens are 5x6 rectangles sharing fence lines; each adds 4 to width
PEN_DEPTH = 6


class Barn(Resource):
    """
    An animal barn in three sizes:
      small  -- open-air fenced pens only
      medium -- pens with corner posts and a flat plank roof
      large  -- full barn shell (plank walls, log frame, gable stair roof,
                open 3-wide entrance) with pens inside along the walls

    Pens are empty (no animals). Each pen gets its own gate on the south side.
    Fixed orientation: gates/entrance face SOUTH. Anchor: NW ground corner.

    Config keys:
        position: [x, y, z]
        size: small | medium | large      (default small)
        pen_count: int                     (default 2; small/medium 1-4, large 2)
        fence_material: str                (default oak_fence)
        frame_material: str                (default dark_oak_log)
        wall_material: str                 (default oak_planks; large only)
        roof_material: str                 (default dark_oak_stairs; large slope)
        flat_roof_material: str            (default oak_planks; medium)
    """

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.position = config["position"]
        self.size = config.get("size", "small")
        if self.size not in ("small", "medium", "large"):
            raise ValueError("size must be small, medium, or large")
        self.pen_count = config.get("pen_count", 2)
        if self.size in ("small", "medium") and not (1 <= self.pen_count <= 4):
            raise ValueError("pen_count must be 1-4 for small/medium barns")
        self.fence_material = config.get("fence_material", "oak_fence")
        self.frame_material = config.get("frame_material", "dark_oak_log")
        self.wall_material = config.get("wall_material", "oak_planks")
        self.roof_material = config.get("roof_material", "dark_oak_stairs")
        self.flat_roof_material = config.get("flat_roof_material", "oak_planks")

    # ---- geometry ----

    def _pens_footprint(self) -> tuple[int, int]:
        return self.pen_count * PEN_SPAN + 1, PEN_DEPTH + 1

    def _footprint(self) -> tuple[int, int]:
        if self.size == "large":
            return 15, 11
        return self._pens_footprint()

    def _gate_block(self) -> str:
        if self.fence_material.endswith("_fence"):
            return self.fence_material.replace("_fence", "_fence_gate")
        return f"{self.fence_material}_gate"

    def _pen_commands(self, x, y, z) -> list[str]:
        """Fenced pens sharing dividers, each with a south gate."""
        cmds = []
        w, d = self._pens_footprint()
        x2 = x + w - 1
        z2 = z + d - 1
        f = self.fence_material

        # Outer rectangle
        cmds.append(f"fill {x} {y+1} {z} {x2} {y+1} {z} minecraft:{f}")
        cmds.append(f"fill {x} {y+1} {z2} {x2} {y+1} {z2} minecraft:{f}")
        cmds.append(f"fill {x} {y+1} {z} {x} {y+1} {z2} minecraft:{f}")
        cmds.append(f"fill {x2} {y+1} {z} {x2} {y+1} {z2} minecraft:{f}")

        # Divider fences between adjacent pens
        for i in range(1, self.pen_count):
            dx = x + i * PEN_SPAN
            cmds.append(f"fill {dx} {y+1} {z} {dx} {y+1} {z2} minecraft:{f}")

        # One gate per pen, centered on its south edge
        for i in range(self.pen_count):
            gx = x + i * PEN_SPAN + PEN_SPAN // 2
            cmds.append(f"setblock {gx} {y+1} {z2} minecraft:{self._gate_block()}[facing=south]")

        return cmds

    def _bounding_box(self):
        x, y, z = self.position
        w, d = self._footprint()
        if self.size == "small":
            h = 3
        elif self.size == "medium":
            h = 6
        else:
            h = 5 + gable_roof_height(d) + 1
        return (x - 1, y, z - 1, x + w, y + h + 1, z + d)

    # ---- Resource interface ----

    def create_commands(self) -> list[str]:
        x, y, z = self.position
        cmds = []

        bx1, by1, bz1, bx2, by2, bz2 = self._bounding_box()
        cmds += clear_volume(bx1, by1 + 1, bz1, bx2, by2, bz2)

        if self.size == "small":
            cmds += self._pen_commands(x, y, z)
            return cmds

        if self.size == "medium":
            w, d = self._pens_footprint()
            x2 = x + w - 1
            z2 = z + d - 1
            cmds += self._pen_commands(x, y, z)
            # Corner posts and a flat roof over the pens
            for px, pz in [(x, z), (x2, z), (x, z2), (x2, z2)]:
                cmds.append(f"fill {px} {y+1} {pz} {px} {y+4} {pz} minecraft:{self.frame_material}")
            cmds.append(f"fill {x-1} {y+5} {z-1} {x2+1} {y+5} {z2+1} minecraft:{self.flat_roof_material}")
            return cmds

        # ---- large: full barn shell with pens inside ----
        w, d = self._footprint()
        x2 = x + w - 1
        z2 = z + d - 1
        wall_h = 5

        # Dirt floor (barns have dirt floors), shell, framing
        cmds.append(f"fill {x} {y} {z} {x2} {y} {z2} minecraft:coarse_dirt")
        cmds += hollow_walls(x, y, z, w, d, wall_h, self.wall_material)
        cmds += corner_frames(x, y, z, w, d, wall_h, self.frame_material)

        # Open entrance: 3 wide, 4 tall, centered on the south wall,
        # framed with logs (big barn doorway, no door blocks)
        ex = x + w // 2
        cmds.append(f"fill {ex-1} {y+1} {z2} {ex+1} {y+4} {z2} minecraft:air")
        cmds.append(f"fill {ex-2} {y+1} {z2} {ex-2} {y+4} {z2} minecraft:{self.frame_material}")
        cmds.append(f"fill {ex+2} {y+1} {z2} {ex+2} {y+4} {z2} minecraft:{self.frame_material}")
        cmds.append(f"fill {ex-2} {y+5} {z2} {ex+2} {y+5} {z2} minecraft:{self.frame_material}")

        # Two interior pens along the west and east walls, central aisle clear
        f = self.fence_material
        pen_z2 = z + 1 + PEN_DEPTH - 1
        for px1, px2 in [(x + 1, x + 5), (x2 - 5, x2 - 1)]:
            cmds.append(f"fill {px1} {y+1} {pen_z2} {px2} {y+1} {pen_z2} minecraft:{f}")
            inner_x = px2 if px1 == x + 1 else px1
            cmds.append(f"fill {inner_x} {y+1} {z+1} {inner_x} {y+1} {pen_z2} minecraft:{f}")
            gx = (px1 + px2) // 2
            cmds.append(f"setblock {gx} {y+1} {pen_z2} minecraft:{self._gate_block()}[facing=south]")

        # Hay bales in the north-end corners for barn flavor
        cmds.append(f"setblock {x+1} {y+1} {z+1} minecraft:hay_block")
        cmds.append(f"setblock {x2-1} {y+1} {z+1} minecraft:hay_block")

        # Gable roof
        cmds += gable_roof(
            x, z, w, d,
            y_base=y + wall_h + 1,
            stair_material=self.roof_material,
            gable_material=self.wall_material,
            overhang=1,
        )

        return cmds

    def destroy_commands(self) -> list[str]:
        bx1, by1, bz1, bx2, by2, bz2 = self._bounding_box()
        return [
            f"fill {bx1} {by1} {bz1} {bx2} {by2} {bz2} minecraft:air",
            f"fill {bx1} {by1} {bz1} {bx2} {by1} {bz2} minecraft:grass_block",
        ]

    def fingerprint(self) -> str:
        raw = (
            f"{self.position}|{self.size}|{self.pen_count}|{self.fence_material}|"
            f"{self.frame_material}|{self.wall_material}|{self.roof_material}|"
            f"{self.flat_roof_material}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()
