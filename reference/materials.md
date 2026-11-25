# Materials

Materials make or break realism more than geometry does. Use `materials.get(preset, color=...)`: the presets hold physically sensible metallic, roughness and transparency values, and the exporter turns them into standard glTF PBR materials.

## Choose the preset, then the colour

1. **Identify what it is made of** from the photos: matte plastic, glossy plastic, painted metal, bare metal, rubber, glass, fabric.
2. Pick the closest preset (names are in [api.md](api.md)); record its colour and any opacity/roughness overrides in the plan.
3. **Set the colour from the photo**, sampled in a well-lit, non-reflective spot. Photos are usually darker or warmer than the true colour, so correct for lighting.

## Rules that prevent fake-looking materials

- **Metallic is 0 or 1.** Plastic, paint, rubber, glass and fabric are 0, even when shiny. Bare metal is 1. Values in between look like dirty chrome.
- **Nothing is pure black or pure white.** Black plastic is about `#151617`–`#2a2c2f`; white plastic and paint about `#e9e9e6`–`#f2f2ef`.
- **Roughness is never 0.** Even polished chrome is about 0.05. Most plastics are 0.3–0.6, rubber 0.8–0.9.
- **Shiny white plastic needs clear coat** (`plastic_glossy` has `coat=0.3`).
- **Alpha is the default portable approximation for transparent parts.** It avoids requiring transmission extensions, but sorting, highlights and apparent darkness vary between Blender and viewers. Leave an actual cavity/backing behind it. For optical refraction, use a supported transmission workflow and verify the destination viewer; do not promise identical rendering everywhere.
- **Two materials on one part are fine** when the real part has two finishes, for example a painted body with a lighter cavity. Assign by `polygon.material_index`.
- **Indicators and screens:** model the lens with `led_lens` or `display_off`, and add `anim.glow_part` for the lit state rather than making the lens emissive all the time.

## Colour checklist against the photos

- Brightness order matches the photo (which part is darkest or lightest).
- Warm versus cool greys match. Many "white" appliances are slightly warm.
- Gloss matches: where the photo shows a sharp highlight, roughness ≤ 0.2; a soft blur means 0.3–0.5; no highlight means ≥ 0.6.
- Metals reflect their surroundings. In renders they look dark if there is nothing to reflect, which is correct; do not fix it by lowering metallic.

## Dark transparent plastics

Separate tint from opacity: a smoky hopper is not clear glass with a pale grey
colour. Compare its brightness against the opaque housing and visible contents in
several labelled photos, including rim thickness and reflections. Start with
`acrylic_smoked`, then adjust tint and alpha together. For example, a deliberately
dark trial might use `color="#282b30", alpha=0.8, roughness=0.12`; these are starting
values, not a match to any particular product. Render over its actual cavity with
consistent lighting and compare to the evidence. Do not lighten it to make the
interior easier to see. Record uncertainty instead of claiming exact colour.

The material cache includes overrides, so different alpha/roughness values produce
different materials. Explicit material names must identify one specification.
