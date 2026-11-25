# PLAN: countertop microwave (worked example)

## Size
480 × 360 × 280 mm (W × D × H), feet included. Source: typical 20 L microwave (no photos for this example), uncertainty ±5 %.
Door and handle add about 60 mm to the depth.

## Parts
| id | name | approx. size (mm) | shape strategy | material | parent |
|---|---|---|---|---|---|
| body | housing | 480 × 360 × 270 | rounded_box r12 + boolean cavity, button pocket, side vents | painted_metal #d9dad7, cavity #bfc2c3 | — |
| control_panel | control panel | 135 × 4 × 240 | rounded_box r1.8, button hole | abs_satin #2a2c2f | — |
| door | door | 334 × 28 × 264 | rounded_box r6 + window opening and glass rebate | abs_satin #2a2c2f | door_hinge |
| door_glass | door window | 214 × 4 × 164 | rounded_slab, corner radius = rebate radius − gap | glass_tinted | door |
| door_handle | door handle | Ø13 bar, 160 tall | sweep along a smooth path | aluminum_brushed | door |
| timer_knob | timer knob | Ø43 × 22 | lathe + grip ridge | abs_satin #c9cbcc | knob_turn |
| power_button | start button | 44 × 12 × 18 | rounded_box r4, sits in a pocket with 3× gap clearance | abs_matte #3a3c40 | power_button_press |
| power_led | power light | Ø7 × 4 | cylinder, bevelled | led_lens | — |
| power_led_glow | power light (on) | lens + gap | anim.glow_part | emissive red | power_led |
| turntable | glass turntable | Ø254 × 13 | lathe | glass_clear | turntable_spin |
| foot_1..4 | rubber feet | Ø28 × 10 | cylinder, bevelled | rubber | — |

## Mating and gaps
Gap = core.gap() = 0.4 mm. Door and panel stand 1 gap in front of the body. Glass sits in a 6 mm rebate with 1 gap all round. Handle legs are screwed into the door (allowed contact).

## Motions
| clip | joint | type | axis | pivot | range |
|---|---|---|---|---|---|
| open_door | door_hinge | hinge | −Z | door's left back edge | 0–105° |
| set_timer | knob_turn | knob | −Y | knob centre | 0–180° |
| power_on | power_button_press + glow | button + light | +Y (into body) | button centre | 3 mm |
| turntable_spin | turntable_spin | knob | Z | cavity centre | 360° in 4 s |
| explode | door_hinge + turntable_extract | hinge then slide | −Z then −Y | door hinge / cavity centre | door 0–105° over 0–1.2 s, held to 3 s; tray waits until 1.2 s, then slides 450 mm out through the opening by 3 s |

## Details (by visibility)
Door window showing the cavity, handle, knob grip, button, LED, panel seam, side vents, feet.

## Assumptions and unknowns
No reference photos: proportions are typical, not measured. Interior (magnetron, light, mica cover) not modelled. Back has no detail.
