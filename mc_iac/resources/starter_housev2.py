import hashlib
from mc_iac.resources.base import Resource
from mc_iac.resources._geometry import (
    clear_volume, hollow_walls, corner_frames, gable_roof, gable_roof_height,
)


# Interior furniture layouts per size preset.
# Interior coordinates: (col, row) with col 0 = west, row 0 = north.
# Each entry: (block_id_with_state, col, row) -- {facing} states point INTO the room.
FURNITURE_LAYOUTS = {
    "small": {
        # 9x8 exterior, 7x6 interior (cols 0-6, rows 0-5)
        "exterior": (9, 8),
        "bed": [
            ("minecraft:red_bed[facing=north,part=foot]", 0, 1),
            ("minecraft:red_bed[facing=north,part=head]", 0, 0),
        ],
        "storage": [
            ("minecraft:chest[facing=west]", 6, 0),
        ],
        "kitchen": [
            ("minecraft:furnace[facing=east]", 0, 3),
            ("minecraft:smoker[facing=east]", 0, 4),
        ],
        "crafting_area": [
            ("minecraft:crafting_table", 6, 2),
            ("minecraft:anvil[facing=west]", 6, 3),
            ("minecraft:blast_furnace[facing=west]", 6, 4),
        ],
        "door_col": 3,          # interior column the door is centered on
        "window_rows": [1, 2],  # interior rows for east/west wall windows
    },
}


class StarterHouse(Resource):
    """
    A medieval-style one-floor starter house with a designed interior:
    kitchen (furnace + smoker), crafting corner (crafting table, anvil,
    blast furnace), bed, and storage chest. Log corner framing, pitched
    stair roof with overhang, windows.

    Fixed orientation for v1: front door faces SOUTH (+z).
    Anchor: north-west floor corner.

    Config keys:
        position: [x, y, z]
        size: "small"                        (presets; only small in v1)
        wall_material: str                    (default oak_planks)
        frame_material: str                   (default dark_oak_log)
        roof_material: str                    (default dark_oak_stairs)
        floor_material: str                   (default stone_bricks)
        include_kitchen: bool                  (default True)
        include_crafting_area: bool            (default True)
        include_bed: bool                      (default True)
        include_storage: bool                  (default True)
    """

    WALL_HEIGHT = 4

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.position = config["position"]
        self.size = config.get("size", "small")
        if self.size not in FURNITURE_LAYOUTS:
            raise ValueError(
                f"Unknown size '{self.size}'. Available: {list(FURNITURE_LAYOUTS.keys())}"
            )
        self.wall_material = config.get("wall_material", "oak_planks")
        self.frame_material = config.get("frame_material", "dark_oak_log")
        self.roof_material = config.get("roof_material", "dark_oak_stairs")
        self.floor_material = config.get("floor_material", "stone_bricks")
        self.include_kitchen = config.get("include_kitchen", True)
        self.include_crafting_area = config.get("include_crafting_area", True)
        self.include_bed = config.get("include_bed", True)
        self.include_storage = config.get("include_storage", True)

        self.layout = FURNITURE_LAYOUTS[self.size]
        self.width, self.depth = self.layout["exterior"]

    def _interior(self, col: int, row: int) -> tuple[int, int]:
        """Interior (col,row) -> absolute (x,z). Interior starts 1 in from the walls."""
        x, _, z = self.position
        return x + 1 + col, z + 1 + row

    def _bounding_box(self):
        x, y, z = self.position
        h = self.WALL_HEIGHT + gable_roof_height(self.depth) + 1
        return (
            x - 1, y, z - 1,
            x + self.width, y + h + 1, z + self.depth,
        )

    def create_commands(self) -> list[str]:
        x, y, z = self.position
        w, d = self.width, self.depth
        x2 = x + w - 1
        z2 = z + d - 1
        cmds = []

        # 0. Clear the whole working volume (including roof overhang)
        bx1, by1, bz1, bx2, by2, bz2 = self._bounding_box()
        cmds += clear_volume(bx1, by1 + 1, bz1, bx2, by2, bz2)

        # 1. Floor
        cmds.append(f"fill {x} {y} {z} {x2} {y} {z2} minecraft:{self.floor_material}")

        # 2. Walls + corner framing
        cmds += hollow_walls(x, y, z, w, d, self.WALL_HEIGHT, self.wall_material)
        cmds += corner_frames(x, y, z, w, d, self.WALL_HEIGHT, self.frame_material)

        # 3. Door: 2-tall opening centered on the south wall, oak door in it
        door_x, _ = self._interior(self.layout["door_col"], 0)
        cmds.append(f"fill {door_x} {y+1} {z2} {door_x} {y+2} {z2} minecraft:air")
        cmds.append(f"setblock {door_x} {y+1} {z2} minecraft:oak_door[half=lower,facing=north,hinge=left]")
        cmds.append(f"setblock {door_x} {y+2} {z2} minecraft:oak_door[half=upper,facing=north,hinge=left]")

        # 4. Windows: east + west walls at the open middle rows, eye level
        for row in self.layout["window_rows"]:
            _, wz = self._interior(0, row)
            cmds.append(f"setblock {x} {y+2} {wz} minecraft:glass_pane")
            cmds.append(f"setblock {x2} {y+2} {wz} minecraft:glass_pane")
        # Two small windows flanking the door on the south wall
        cmds.append(f"setblock {x+2} {y+2} {z2} minecraft:glass_pane")
        cmds.append(f"setblock {x2-2} {y+2} {z2} minecraft:glass_pane")

        # 5. Interior furniture (feature toggles)
        toggles = {
            "kitchen": self.include_kitchen,
            "crafting_area": self.include_crafting_area,
            "bed": self.include_bed,
            "storage": self.include_storage,
        }
        for zone, enabled in toggles.items():
            if not enabled:
                continue
            for block, col, row in self.layout[zone]:
                fx, fz = self._interior(col, row)
                cmds.append(f"setblock {fx} {y+1} {fz} {block}")

        # 6. Interior lighting: two torches on the north wall, always included
        tx1, tz = self._interior(2, 0)
        tx2, _ = self._interior(4, 0)
        cmds.append(f"setblock {tx1} {y+3} {tz} minecraft:wall_torch[facing=south]")
        cmds.append(f"setblock {tx2} {y+3} {tz} minecraft:wall_torch[facing=south]")

        # 7. Gable roof with overhang; gable end-walls filled with wall material
        cmds += gable_roof(
            x, z, w, d,
            y_base=y + self.WALL_HEIGHT + 1,
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
            f"{self.position}|{self.size}|{self.wall_material}|{self.frame_material}|"
            f"{self.roof_material}|{self.floor_material}|{self.include_kitchen}|"
            f"{self.include_crafting_area}|{self.include_bed}|{self.include_storage}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()
