import hashlib
from mc_iac.resources.base import Resource


class Well(Resource):
    """
    A village-style well: cobblestone rim around a 3x3 water shaft,
    four fence posts, and a slab canopy.

    Footprint: 5x5, anchored at the north-west corner.

    Config keys:
        position: [x, y, z]         -- NW corner, ground level
        material: str                -- structure material (default cobblestone)
        roof_material: str           -- canopy slab (default cobblestone_slab)
        fence_material: str          -- posts (default oak_fence)
        shaft_depth: int             -- water depth below ground (default 3)
    """

    WIDTH = 5
    DEPTH = 5

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.position = config["position"]
        self.material = config.get("material", "cobblestone")
        self.roof_material = config.get("roof_material", "cobblestone_slab")
        self.fence_material = config.get("fence_material", "oak_fence")
        self.shaft_depth = config.get("shaft_depth", 3)

    def create_commands(self) -> list[str]:
        x, y, z = self.position
        x2 = x + self.WIDTH - 1
        z2 = z + self.DEPTH - 1
        m = self.material
        cmds = []

        # Clear the above-ground volume
        cmds.append(f"fill {x} {y+1} {z} {x2} {y+6} {z2} minecraft:air")

        # Solid foundation cube from shaft bottom up to ground level
        cmds.append(f"fill {x} {y-self.shaft_depth} {z} {x2} {y} {z2} minecraft:{m}")

        # Carve the 3x3 interior shaft and fill with water sources
        cmds.append(
            f"fill {x+1} {y-self.shaft_depth+1} {z+1} {x2-1} {y} {z2-1} minecraft:water"
        )

        # Rim ring one block above ground (walkable lip around the water)
        cmds.append(f"fill {x} {y+1} {z} {x2} {y+1} {z} minecraft:{m}")
        cmds.append(f"fill {x} {y+1} {z2} {x2} {y+1} {z2} minecraft:{m}")
        cmds.append(f"fill {x} {y+1} {z} {x} {y+1} {z2} minecraft:{m}")
        cmds.append(f"fill {x2} {y+1} {z} {x2} {y+1} {z2} minecraft:{m}")

        # Four fence posts at the corners, 3 tall above the rim
        for px, pz in [(x, z), (x2, z), (x, z2), (x2, z2)]:
            cmds.append(f"fill {px} {y+2} {pz} {px} {y+4} {pz} minecraft:{self.fence_material}")

        # Slab canopy
        cmds.append(f"fill {x} {y+5} {z} {x2} {y+5} {z2} minecraft:{self.roof_material}[type=bottom]")

        return cmds

    def destroy_commands(self) -> list[str]:
        x, y, z = self.position
        x2 = x + self.WIDTH - 1
        z2 = z + self.DEPTH - 1
        return [
            # Remove everything above ground
            f"fill {x} {y+1} {z} {x2} {y+6} {z2} minecraft:air",
            # Refill the shaft with dirt and re-cap with grass at ground level
            f"fill {x} {y-self.shaft_depth} {z} {x2} {y-1} {z2} minecraft:dirt",
            f"fill {x} {y} {z} {x2} {y} {z2} minecraft:grass_block",
        ]

    def fingerprint(self) -> str:
        raw = (
            f"{self.position}|{self.material}|{self.roof_material}|"
            f"{self.fence_material}|{self.shaft_depth}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()
