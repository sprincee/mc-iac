import hashlib
from mc_iac.resources.base import Resource
from mc_iac.resources._geometry import (
    clear_volume, hollow_walls, corner_frames, gable_roof, gable_roof_height,
)


class Blacksmith(Resource):
    """
    A medieval blacksmith, modeled on the vanilla village weaponsmith:
    an enclosed work room (crafting/smithing/grindstone/anvil) plus an
    open-fronted forge porch with a furnace bank and a decorative lava
    basin contained in stone and iron bars.

    FIRE SAFETY (hard requirement from the design doc):
      - The floor is stone bricks everywhere; the lava basin is recessed
        into that stone floor, ringed by iron bars at standing height.
      - No flammable block (wood, fences, planks) is placed within 2
        blocks of the lava cells. The layout enforces this by
        construction.
      - Lava source blocks are placed LAST in the command list, so lava
        never exists un-contained even mid-apply.

    Footprint: 11 wide x 8 deep. Fixed orientation: the open porch
    entrance faces SOUTH. Anchor: NW floor corner.

    Config keys:
        position: [x, y, z]
        wall_material: str          (default cobblestone)
        frame_material: str         (default oak_log)
        floor_material: str         (default stone_bricks -- keep it
                                     non-flammable; this floor contains the lava)
        roof_material: str          (default dark_oak_stairs)
        include_forge: bool          (default True: furnaces + lava feature)
        include_workbenches: bool    (default True)
    """

    WIDTH = 11
    DEPTH = 8
    WALL_HEIGHT = 4

    NONFLAMMABLE_FLOORS = {
        "stone_bricks", "cobblestone", "stone", "deepslate_bricks",
        "polished_andesite", "bricks", "smooth_stone",
    }

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.position = config["position"]
        self.wall_material = config.get("wall_material", "cobblestone")
        self.frame_material = config.get("frame_material", "oak_log")
        self.floor_material = config.get("floor_material", "stone_bricks")
        self.roof_material = config.get("roof_material", "dark_oak_stairs")
        self.include_forge = config.get("include_forge", True)
        self.include_workbenches = config.get("include_workbenches", True)

        if self.include_forge and self.floor_material not in self.NONFLAMMABLE_FLOORS:
            raise ValueError(
                f"floor_material '{self.floor_material}' is not in the known "
                f"non-flammable set {sorted(self.NONFLAMMABLE_FLOORS)} -- the "
                f"blacksmith floor contains the lava basin and must not burn."
            )

    def _bounding_box(self):
        x, y, z = self.position
        h = self.WALL_HEIGHT + gable_roof_height(self.DEPTH) + 1
        return (x - 1, y, z - 1, x + self.WIDTH, y + h + 1, z + self.DEPTH)

    def create_commands(self) -> list[str]:
        x, y, z = self.position
        w, d = self.WIDTH, self.DEPTH
        x2 = x + w - 1
        z2 = z + d - 1
        cmds = []
        lava_cmds = []  # collected separately, appended LAST

        bx1, by1, bz1, bx2, by2, bz2 = self._bounding_box()
        cmds += clear_volume(bx1, by1 + 1, bz1, bx2, by2, bz2)

        # Stone brick floor across the whole footprint (contains the lava)
        cmds.append(f"fill {x} {y} {z} {x2} {y} {z2} minecraft:{self.floor_material}")

        # Shell + framing
        cmds += hollow_walls(x, y, z, w, d, self.WALL_HEIGHT, self.wall_material)
        cmds += corner_frames(x, y, z, w, d, self.WALL_HEIGHT, self.frame_material)

        # Open porch entrance: 4-wide opening in the south wall's east half
        ox1, ox2 = x + 6, x + 9
        cmds.append(f"fill {ox1} {y+1} {z2} {ox2} {y+3} {z2} minecraft:air")
        # Log jambs on either side of the opening
        cmds.append(f"fill {ox1-1} {y+1} {z2} {ox1-1} {y+self.WALL_HEIGHT} {z2} minecraft:{self.frame_material}")

        # Work room door on the south wall's west half
        dx = x + 3
        cmds.append(f"fill {dx} {y+1} {z2} {dx} {y+2} {z2} minecraft:air")
        cmds.append(f"setblock {dx} {y+1} {z2} minecraft:oak_door[half=lower,facing=north,hinge=left]")
        cmds.append(f"setblock {dx} {y+2} {z2} minecraft:oak_door[half=upper,facing=north,hinge=left]")

        # Windows: west wall and north wall (west half)
        cmds.append(f"setblock {x} {y+2} {z+3} minecraft:glass_pane")
        cmds.append(f"setblock {x} {y+2} {z+4} minecraft:glass_pane")
        cmds.append(f"setblock {x+2} {y+2} {z} minecraft:glass_pane")
        cmds.append(f"setblock {x+4} {y+2} {z} minecraft:glass_pane")

        # Work area along the west interior wall
        if self.include_workbenches:
            cmds.append(f"setblock {x+1} {y+1} {z+1} minecraft:crafting_table")
            cmds.append(f"setblock {x+1} {y+1} {z+2} minecraft:smithing_table")
            cmds.append(f"setblock {x+1} {y+1} {z+3} minecraft:grindstone[face=floor,facing=east]")
            cmds.append(f"setblock {x+1} {y+1} {z+4} minecraft:anvil[facing=east]")

        # Forge: furnace bank against the north wall of the porch area
        if self.include_forge:
            cmds.append(f"setblock {x+7} {y+1} {z+1} minecraft:furnace[facing=south]")
            cmds.append(f"setblock {x+8} {y+1} {z+1} minecraft:furnace[facing=south]")
            cmds.append(f"setblock {x+9} {y+1} {z+1} minecraft:blast_furnace[facing=south]")

            # Lava basin: two floor cells become lava, ringed by iron bars.
            # Basin cells: (x+7, z+4) and (x+8, z+4).
            # Everything within 1 block is stone-brick floor, iron bars, or air.
            bars = [
                (x + 6, z + 4), (x + 9, z + 4),
                (x + 7, z + 3), (x + 8, z + 3),
                (x + 7, z + 5), (x + 8, z + 5),
            ]
            for bxp, bzp in bars:
                cmds.append(f"setblock {bxp} {y+1} {bzp} minecraft:iron_bars")

            # Lava LAST -- basin is fully built before any lava exists
            lava_cmds.append(f"setblock {x+7} {y} {z+4} minecraft:lava")
            lava_cmds.append(f"setblock {x+8} {y} {z+4} minecraft:lava")

        # Interior torches
        cmds.append(f"setblock {x+2} {y+3} {z+1} minecraft:wall_torch[facing=south]")

        # Gable roof over the whole footprint
        cmds += gable_roof(
            x, z, w, d,
            y_base=y + self.WALL_HEIGHT + 1,
            stair_material=self.roof_material,
            gable_material=self.wall_material,
            overhang=1,
        )

        return cmds + lava_cmds

    def destroy_commands(self) -> list[str]:
        x, y, z = self.position
        bx1, by1, bz1, bx2, by2, bz2 = self._bounding_box()
        return [
            # Remove lava FIRST so nothing flows while the shell comes down
            f"fill {x+7} {y} {z+4} {x+8} {y} {z+4} minecraft:stone_bricks",
            f"fill {bx1} {by1} {bz1} {bx2} {by2} {bz2} minecraft:air",
            f"fill {bx1} {by1} {bz1} {bx2} {by1} {bz2} minecraft:grass_block",
        ]

    def fingerprint(self) -> str:
        raw = (
            f"{self.position}|{self.wall_material}|{self.frame_material}|"
            f"{self.floor_material}|{self.roof_material}|{self.include_forge}|"
            f"{self.include_workbenches}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()
