# Goth-girl character art (layered rig)

Each character is a folder of **transparent PNG layers**. The rig
(`visualizers/alt_gothic/rig.py`) loads `assets/characters/<name>/<layer>.png`
and animates each layer independently. Any missing layer falls back to a
procedural silhouette, so you can add art one layer at a time.

```
assets/characters/
  goth_a/            # used by the two big front characters
    hair_back.png
    torso.png        # body + dress (this is the only required layer)
    head.png
    arm_l.png
    arm_r.png
    hair_front.png   # optional side bangs
  goth_b/            # the centre back character
  goth_c/            # the two small side back characters
```

The renderer currently references `goth_a` (front pair), `goth_b` (centre back)
and `goth_c` (side back). Add those three folders.

## Layer rules (important for clean animation)

| Layer        | Pivot (rotation point) | Notes |
|--------------|------------------------|-------|
| `hair_back`  | centre of the head     | sways with the bass |
| `torso`      | base of the neck       | body + dress, drawn from shoulders down |
| `head`       | centre of the head     | bobs on the beat |
| `arm_l`      | **the shoulder**       | arm hanging straight **down**; rig rotates it up |
| `arm_r`      | **the shoulder**       | mirror of arm_l |
| `hair_front` | centre of the head     | optional bangs in front of the face |

Critical for arms: draw each arm **hanging straight down from the shoulder**,
with the shoulder joint at the **top-centre** of the image. The rig rotates the
arm about that top-centre point — 0° = down, ~165° = raised overhead. If the
arm is drawn already raised, the animation will look wrong.

Export each layer on its own transparent canvas, all layers the **same canvas
size** and aligned (so they overlay correctly).

## AI generation prompts

Generate in your image tool of choice (Midjourney / DALL·E / Stable Diffusion).
Ask for a **front-facing, symmetrical, full-body** character on a **transparent
/ plain background**, then either export parts directly or cut them in an editor.

**Base character (one image, then slice):**
> full-body goth girl, anime style, front view, symmetrical T-pose with arms
> hanging straight down, black gothic dress, choker, fishnet, pale skin, long
> dark hair, dramatic eye makeup, clean flat colors, thick outline, centered,
> plain transparent background, full body visible head to toe

**Per-layer (if your tool supports isolated parts):**
- `torso`: "goth girl torso and black dress only, no head, no arms, front view, transparent background"
- `head`: "goth girl head and face only, front view, choker, transparent background"
- `hair_back`: "long dark hair back layer only, transparent background"
- `arm_l` / `arm_r`: "single goth girl arm hanging straight down, lace sleeve, hand at bottom, transparent background"

Variations: change `hair_hue`, dress accents, or generate distinct `goth_a/b/c`
for variety. Keep the same framing/scale across a character's layers.

## Minimum viable

Just drop a single `torso.png` per character to instantly replace the body
silhouette with real art; add `head` + arms next for full articulation.
