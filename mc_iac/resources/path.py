import hashlib
from mc_iac.resources.base import Resource

DEFAULT_PALETTE = {
    "dirt_path": 0.6,
    "gravel": 0.25,
    "coarse_dirt": 0.15,
}

EDGE_SKIP_PROBABILITY = 0.35


def _noise(x: int, z: int, seed: int, salt: str) -> float:
    """Deterministic per-block pseudo-random value in [0, 1)."""
    raw = f"{x},{z},{seed},{salt}".encode()
    digest = hashlib.sha256(raw).hexdigest()
    return (int(digest, 16) % 1_000_000) / 1_000_000


class Path(Resource):
    """
    A noise-textured path connecting two points, mixing a weighted
    palette of ground blocks with ragged edges so it reads as organic
    against any structure it meets.

    Fully deterministic: the same config + seed always generates the
    exact same blocks (required for fingerprint/idempotency guarantees).

    Config keys:
        from: [x, y, z]
        to: [x, y, z]
        width: int                (default 3)
        seed: int                 (default 0)
        blocks: {block: weight}   (default dirt_path/gravel/coarse_dirt mix)
    """

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.start = config["from"]
        self.end = config["to"]
        self.width = config.get("width", 3)
        if self.width < 1:
            raise ValueError("width must be at least 1")
        self.seed = config.get("seed", 0)
        self.palette = config.get("blocks", dict(DEFAULT_PALETTE))
        total = sum(self.palette.values())
        if total <= 0:
            raise ValueError("palette weights must sum to a positive number")
        # Normalize weights, keep deterministic ordering
        self.palette = {k: v / total for k, v in sorted(self.palette.items())}

    # ---- geometry ----

    def _line_cells(self) -> list[tuple[int, int]]:
        """Bresenham line between start and end on the x/z plane."""
        x1, _, z1 = self.start
        x2, _, z2 = self.end
        cells = []
        dx = abs(x2 - x1)
        dz = abs(z2 - z1)
        sx = 1 if x2 >= x1 else -1
        sz = 1 if z2 >= z1 else -1
        err = dx - dz
        x, z = x1, z1
        while True:
            cells.append((x, z))
            if x == x2 and z == z2:
                break
            e2 = 2 * err
            if e2 > -dz:
                err -= dz
                x += sx
            if e2 < dx:
                err += dx
                z += sz
        return cells

    def _path_cells(self) -> set[tuple[int, int]]:
        """Stamp the line to the configured width, jittering the edges."""
        line = self._line_cells()
        x1, _, z1 = self.start
        x2, _, z2 = self.end
        # Perpendicular axis: widen across z if the path runs mostly east-west
        widen_z = abs(x2 - x1) >= abs(z2 - z1)
        half = self.width // 2

        cells = set()
        for (x, z) in line:
            for off in range(-half, half + 1):
                cx, cz = (x, z + off) if widen_z else (x + off, z)
                is_edge = self.width > 1 and abs(off) == half
                if is_edge and _noise(cx, cz, self.seed, "edge") < EDGE_SKIP_PROBABILITY:
                    continue
                cells.add((cx, cz))
        return cells

    def _pick_block(self, x: int, z: int) -> str:
        v = _noise(x, z, self.seed, "palette")
        cumulative = 0.0
        for block, weight in self.palette.items():
            cumulative += weight
            if v < cumulative:
                return block
        return next(iter(self.palette))  # float rounding fallback

    # ---- Resource interface ----

    def create_commands(self) -> list[str]:
        y = self.start[1]
        cmds = []
        for (x, z) in sorted(self._path_cells()):
            block = self._pick_block(x, z)
            cmds.append(f"setblock {x} {y} {z} minecraft:{block}")
        return cmds

    def destroy_commands(self) -> list[str]:
        y = self.start[1]
        return [
            f"setblock {x} {y} {z} minecraft:grass_block"
            for (x, z) in sorted(self._path_cells())
        ]

    def fingerprint(self) -> str:
        raw = f"{self.start}|{self.end}|{self.width}|{self.seed}|{self.palette}"
        return hashlib.sha256(raw.encode()).hexdigest()
