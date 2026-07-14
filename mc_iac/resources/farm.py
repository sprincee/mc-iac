import hashlib
from mc_iac.resources.base import Resource

# crop -> (ground block, crop block, max age)
CROP_TABLE = {
    "wheat": ("farmland[moisture=7]", "wheat", 7),
    "carrot": ("farmland[moisture=7]", "carrots", 7),
    "potato": ("farmland[moisture=7]", "potatoes", 7),
    "beetroot": ("farmland[moisture=7]", "beetroots", 3),
    "nether_wart": ("soul_sand", "nether_wart", 3),
}


class Farm(Resource):
    """
    A circular crop farm surrounded by a fence ring with a gate.

    Basic crops (wheat/carrot/potato/beetroot) grow on hydrated farmland
    with embedded water sources. The nether_wart variant grows on soul
    sand and needs no water.

    Config keys:
        position: [x, y, z]      -- CENTER of the circle, ground level
        radius: int               -- crop circle radius in blocks (min 4)
        crop: str                 -- wheat | carrot | potato | beetroot | nether_wart
        age: int                  -- crop growth stage (default: max age, looks best)
        fence_material: str       -- default oak_fence
        gate_facing: str          -- north | south | east | west (default south)
    """

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.position = config["position"]
        self.radius = config.get("radius", 6)
        if self.radius < 4:
            raise ValueError("radius must be at least 4")
        self.crop = config.get("crop", "wheat")
        if self.crop not in CROP_TABLE:
            raise ValueError(f"Unknown crop '{self.crop}'. Options: {list(CROP_TABLE.keys())}")
        _, _, max_age = CROP_TABLE[self.crop]
        self.age = config.get("age", max_age)
        if not (0 <= self.age <= max_age):
            raise ValueError(f"age for {self.crop} must be 0..{max_age}")
        self.fence_material = config.get("fence_material", "oak_fence")
        self.gate_facing = config.get("gate_facing", "south")
        if self.gate_facing not in ("north", "south", "east", "west"):
            raise ValueError("gate_facing must be north/south/east/west")

    # ---- geometry helpers ----

    def _inside_cells(self) -> set[tuple[int, int]]:
        r = self.radius
        return {
            (dx, dz)
            for dx in range(-r, r + 1)
            for dz in range(-r, r + 1)
            if dx * dx + dz * dz <= r * r
        }

    def _ring_cells(self, inside: set) -> set[tuple[int, int]]:
        """Cells just outside the circle, 8-adjacent to an inside cell."""
        ring = set()
        for (dx, dz) in inside:
            for ox in (-1, 0, 1):
                for oz in (-1, 0, 1):
                    n = (dx + ox, dz + oz)
                    if n not in inside:
                        ring.add(n)
        return ring

    def _water_cells(self, inside: set) -> set[tuple[int, int]]:
        """Water sources so all farmland is within hydration range (4 blocks)."""
        if self.crop == "nether_wart":
            return set()
        if self.radius <= 4:
            return {(0, 0)}
        half = self.radius // 2
        candidates = {(0, 0), (half, 0), (-half, 0), (0, half), (0, -half)}
        return {c for c in candidates if c in inside}

    def _gate_cell(self) -> tuple[int, int]:
        r = self.radius + 1
        return {
            "north": (0, -r),
            "south": (0, r),
            "west": (-r, 0),
            "east": (r, 0),
        }[self.gate_facing]

    # ---- Resource interface ----

    def create_commands(self) -> list[str]:
        cx, y, cz = self.position
        ground_block, crop_block, _ = CROP_TABLE[self.crop]
        inside = self._inside_cells()
        ring = self._ring_cells(inside)
        water = self._water_cells(inside)
        gate = self._gate_cell()
        r = self.radius + 1

        cmds = []
        # Clear above-ground layer over the whole footprint
        cmds.append(f"fill {cx-r} {y+1} {cz-r} {cx+r} {y+2} {cz+r} minecraft:air")

        for (dx, dz) in sorted(inside):
            bx, bz = cx + dx, cz + dz
            if (dx, dz) in water:
                cmds.append(f"setblock {bx} {y} {bz} minecraft:water")
            else:
                cmds.append(f"setblock {bx} {y} {bz} minecraft:{ground_block}")
                cmds.append(f"setblock {bx} {y+1} {bz} minecraft:{crop_block}[age={self.age}]")

        for (dx, dz) in sorted(ring):
            bx, bz = cx + dx, cz + dz
            if (dx, dz) == gate:
                axis_facing = self.gate_facing
                cmds.append(
                    f"setblock {bx} {y+1} {bz} minecraft:{self.fence_material}_gate[facing={axis_facing}]"
                    if not self.fence_material.endswith("_fence")
                    else f"setblock {bx} {y+1} {bz} "
                         f"minecraft:{self.fence_material.replace('_fence', '_fence_gate')}[facing={axis_facing}]"
                )
            else:
                cmds.append(f"setblock {bx} {y+1} {bz} minecraft:{self.fence_material}")

        return cmds

    def destroy_commands(self) -> list[str]:
        cx, y, cz = self.position
        r = self.radius + 1
        return [
            f"fill {cx-r} {y+1} {cz-r} {cx+r} {y+2} {cz+r} minecraft:air",
            f"fill {cx-r} {y} {cz-r} {cx+r} {y} {cz+r} minecraft:grass_block",
        ]

    def fingerprint(self) -> str:
        raw = (
            f"{self.position}|{self.radius}|{self.crop}|{self.age}|"
            f"{self.fence_material}|{self.gate_facing}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()
