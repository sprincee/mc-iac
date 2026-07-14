# TerraCraft

**Infrastructure as Code for Minecraft.** Declare structures in YAML, run `plan` to preview changes, `apply` to provision them on a live server, `destroy` to tear them down — the Terraform workflow, pointed at a Minecraft world over RCON.

```yaml
stack_name: my-village
resources:
  - type: starter_house
    name: home
    position: [100, -60, 100]
    size: small
    wall_material: oak_planks
    roof_material: dark_oak_stairs

  - type: farm
    name: carrot_farm
    position: [126, -60, 116]
    radius: 6
    crop: carrot

  - type: path
    name: home_to_farm
    from: [104, -60, 109]
    to: [118, -60, 116]
    width: 3
    seed: 7
```

```
$ python cli.py plan --spec specs/village.yaml
Stack: my-village

  + create   StarterHouse         home
  + create   Farm                 carrot_farm
  + create   Path                 home_to_farm

Plan: 3 to create, 0 to update, 0 to destroy.
```

<!-- TODO: demo GIF here — YAML -> apply -> village materializes -->

## Why

I wanted to internalize how IaC tools actually work — not just use Terraform, but build the plan/apply lifecycle, state tracking, and diffing myself. Minecraft turned out to be a great target: a live, mutable environment you can provision against over a wire protocol (RCON), where "drift" is someone punching a hole in your wall.

## How it works

The engine mirrors Terraform's core loop:

1. **Spec** (`spec.py`) — YAML files are parsed into resource objects via a registry that maps `type:` strings to Python classes. Adding a resource type is one class + one registry line.
2. **State** (`state.py`) — every applied resource is recorded with a SHA-256 fingerprint of its full config. Each spec file gets its own isolated state file (like Terraform workspaces).
3. **Diff** (`diff.py`) — set operations over resource names decide the plan: in spec but not state → create; in both with mismatched fingerprints → update; in state but not spec → destroy. `plan` is strictly read-only.
4. **Apply** — generated Minecraft commands are executed over a single batched RCON connection; state is written only after commands succeed.

## Resource types

| Type | What it provisions |
|---|---|
| `command_block` | A single command block (impulse/chain/repeat) |
| `well` | Village-style well: water shaft, fence posts, canopy |
| `starter_house` | Medieval one-floor house — log framing, gable roof, windows, furnished interior (kitchen, crafting corner, bed, storage) with feature toggles |
| `farm` | Circular fenced crop farm — wheat/carrot/potato/beetroot, plus nether wart on soul sand |
| `path` | Noise-textured path connecting structures; hash-based noise so the same seed always produces identical blocks (idempotency) |
| `enchanting_tower` | Multi-floor tower with ladder, windows, and a bookshelf-ringed enchanting table on top |
| `barn` | Three size presets: open pens → covered pens → full barn with gable roof |
| `blacksmith` | Smithy with an open forge porch and a lava feature — flammable floor materials are rejected at load time, and lava is placed last during apply so it never exists uncontained |

Structures with designed interiors use **size presets** (`small`/`medium`/`large`) rather than freeform dimensions — constraining the parameter space guarantees every output is a valid, hand-designed layout. Cosmetics (materials) and features (`include_kitchen: true`) stay configurable.

## Quickstart

Requirements: Python 3.11+, a Minecraft Java Edition server (Paper recommended) with RCON enabled.

```bash
git clone https://github.com/sprincee/mc-iac.git
cd mc-iac
python -m venv venv && source venv/bin/activate   # Windows: .\venv\Scripts\Activate.ps1
pip install mcrcon pyyaml
```

In your server's `server.properties`:

```
enable-rcon=true
rcon.port=25575
rcon.password=<your password>
```

Configure the connection (defaults: `localhost:25575`):

```bash
export MC_IAC_RCON_PASSWORD=<your password>    # PowerShell: $env:MC_IAC_RCON_PASSWORD="..."
```

Provision:

```bash
python cli.py plan    --spec specs/well.yaml
python cli.py apply   --spec specs/well.yaml
python cli.py destroy --spec specs/well.yaml
```

## Design notes & lessons

- **Fingerprints over field diffs.** Each resource hashes its entire config; the diff engine compares hashes, not fields. Simple, and sufficient to drive correct create/update/destroy decisions.
- **Determinism is a hard requirement.** The path resource uses SHA-256-based per-block noise instead of `random` — the same spec must always generate the same commands, or idempotency and fingerprinting silently break.
- **Triggered mechanisms provision reliably; self-oscillating ones don't.** An earlier redstone clock resource failed consistently: circuits assembled instantly via commands don't receive the block-update cascade that hand-placement triggers, and settle into stable equilibrium instead of oscillating. Structures and lever-triggered mechanisms have no such failure mode — the project pivoted accordingly.
- **Safety by construction.** The blacksmith validates floor materials against a non-flammable allowlist at load time and orders lava placement last, so no intermediate apply state can start a fire.

## Known limitations / roadmap

- `destroy` needs the resource definition still present in the spec to know its geometry; real Terraform stores enough in state to destroy independently. Fix: persist bounding boxes in state.
- All structures are fixed-orientation (south-facing). A `facing` parameter is the next planned feature.
- Path endpoints are explicit coordinates; referencing other resources by name (`from_resource: home`) would introduce a dependency graph — the natural v2.
- Drift detection (`refresh`): polling the live world to catch manual edits, closing the loop with Terraform's refresh.

## License

Copyright (c) 2011-2026 Mahad Khan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.