import hashlib
from mc_iac.resources.base import Resource
from mc_iac.resources._geometry import (
    clear_volume, hollow_walls, corner_frames, pyramid_roof,
)

FLOOR_HEIGHT = 4  # vertical blocks per storey (3 air + 1 floor slab)


class EnchantingTower(Resource):
    """
    A multi-floor tower, village-church style: cobblestone walls with
    oak log corner framing and glass pane windows. All floors are empty
    except the top, which has an enchanting table ringed by bookshelves.
    A ladder on the north interior wall connects the floors.

    Fixed orientation: door faces SOUTH. Anchor: NW floor corner.

    Config keys:
        position: [x, y, z]
        floors: int              (default 3, range 2-5)
        footprint: int            (default 7; forced odd so the table centers)
        wall_material: str        (default cobblestone)
        frame_material: str       (default oak_log)
        floor_material: str       (default oak_planks)
        window_material: str      (default glass_pane)
        roof_material: str        (default cobblestone_stairs)
    """

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.position = config["position"]
        self.floors = config.get("floors", 3)
        if not (2 <= self.floors <= 5):
            raise ValueError("floors must be between 2 and 5")
        self.footprint = config.get("footprint", 7)
        if self.footprint < 5:
            raise ValueError("footprint must be at least 5")
        if self.footprint % 2 == 0:
            self.footprint += 1  # force odd so the enchanting table centers
        self.wall_material = config.get("wall_material", "cobblestone")
        self.frame_material = config.get("frame_material", "oak_log")
        self.floor_material = config.get("floor_material", "oak_planks")
        self.window_material = config.get("window_material", "glass_pane")
        self.roof_material = config.get("roof_material", "cobblestone_stairs")

    def _wall_height(self) -> int:
        return self.floors * FLOOR_HEIGHT

    def _ladder_cell(self) -> tuple[int, int]:
        """Ladder column: center of the north interior wall."""
        x, _, z = self.position
        return x + self.footprint // 2, z + 1

    def _bounding_box(self):
        x, y, z = self.position
        f = self.footprint
        roof_levels = (f + 2) // 2 + 1
        return (
            x - 1, y, z - 1,
            x + f, y + self._wall_height() + roof_levels + 1, z + f,
        )

    def create_commands(self) -> list[str]:
        x, y, z = self.position
        f = self.footprint
        x2 = x + f - 1
        z2 = z + f - 1
        h = self._wall_height()
        cmds = []

        bx1, by1, bz1, bx2, by2, bz2 = self._bounding_box()
        cmds += clear_volume(bx1, by1 + 1, bz1, bx2, by2, bz2)

        # Ground floor + shell
        cmds.append(f"fill {x} {y} {z} {x2} {y} {z2} minecraft:{self.floor_material}")
        cmds += hollow_walls(x, y, z, f, f, h, self.wall_material)
        cmds += corner_frames(x, y, z, f, f, h, self.frame_material)

        # Door: south wall, centered, 2 tall
        dx = x + f // 2
        cmds.append(f"fill {dx} {y+1} {z2} {dx} {y+2} {z2} minecraft:air")
        cmds.append(f"setblock {dx} {y+1} {z2} minecraft:oak_door[half=lower,facing=north,hinge=left]")
        cmds.append(f"setblock {dx} {y+2} {z2} minecraft:oak_door[half=upper,facing=north,hinge=left]")

        # Intermediate floor slabs (with a hole for the ladder)
        lx, lz = self._ladder_cell()
        for storey in range(1, self.floors):
            fy = y + storey * FLOOR_HEIGHT
            cmds.append(f"fill {x+1} {fy} {z+1} {x2-1} {fy} {z2-1} minecraft:{self.floor_material}")
            cmds.append(f"setblock {lx} {fy} {lz} minecraft:air")

        # Ladder column on the north interior wall, ground to top floor
        cmds.append(f"fill {lx} {y+1} {lz} {lx} {y+h-1} {lz} minecraft:ladder[facing=south]")

        # Windows: centered on each wall, each storey, 1x2 tall at eye level.
        # Skip the north wall (ladder side) and the ground-floor south wall (door).
        mid = f // 2
        for storey in range(self.floors):
            wy = y + storey * FLOOR_HEIGHT + 2
            cmds.append(f"fill {x} {wy} {z+mid} {x} {wy+1} {z+mid} minecraft:{self.window_material}")
            cmds.append(f"fill {x2} {wy} {z+mid} {x2} {wy+1} {z+mid} minecraft:{self.window_material}")
            if storey > 0:
                cmds.append(f"fill {x+mid} {wy} {z2} {x+mid} {wy+1} {z2} minecraft:{self.window_material}")

        # Top floor: enchanting table centered, bookshelves on the interior
        # perimeter (skipping the ladder cell and its two neighbors for access)
        top_y = y + (self.floors - 1) * FLOOR_HEIGHT + 1
        cx, cz = x + mid, z + mid
        cmds.append(f"setblock {cx} {top_y} {cz} minecraft:enchanting_table")

        skip = {(lx, lz), (lx - 1, lz), (lx + 1, lz)}
        for px in range(x + 1, x2):
            for pz in range(z + 1, z2):
                on_perimeter = px in (x + 1, x2 - 1) or pz in (z + 1, z2 - 1)
                if on_perimeter and (px, pz) not in skip:
                    cmds.append(f"setblock {px} {top_y} {pz} minecraft:bookshelf")

        # Torch above the enchanting table area
        cmds.append(f"setblock {cx} {top_y+2} {cz+1} minecraft:torch")

        # Pyramid roof
        cmds += pyramid_roof(
            x, z, f, f,
            y_base=y + h + 1,
            stair_material=self.roof_material,
            cap_material=self.frame_material,
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
            f"{self.position}|{self.floors}|{self.footprint}|{self.wall_material}|"
            f"{self.frame_material}|{self.floor_material}|{self.window_material}|"
            f"{self.roof_material}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()
