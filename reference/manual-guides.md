# Manual walkthroughs

The model and part metadata are the primary deliverables. Demonstrate them with a continuous named clip, `how_to_use`, with evidence-labeled instructions and chapters in the export manifest. Each chapter inherits the previous
state. Independent clips remain optional exploration controls. Never implement the
guide by autoplaying independent clips that each reset to rest.

Write a storyboard before animation: step ID, instruction, verified manual PDF
page/figure, initial and resulting state, mechanical targets, action duration, hold,
and pause-after. Keep installation, everyday operation and maintenance as distinct
supported tasks rather than one arbitrary disassembly tour. Choose one as primary.
Real-world activities such as filling or app setup may be a caption/hold with an
explicit user pause. Do not fabricate food flow, app screens or network success.

```python
g = anim.guide()
evidence = [{"source":"manual.pdf", "locator":"verified PDF page and figure"}]
g.step("open", "Open the lid", {lid_hinge:100}, evidence=evidence)
g.step("prepare", "Complete the evidenced preparation task", seconds=.5,
       hold=1, evidence=evidence, pause_after=True)
g.step("close", "Close the lid", {lid_hinge:0}, evidence=evidence)
g.finish()
```

The example is illustrative, not a validated procedure. Targets are joint objects
or registered glow parts. All changes use a single track per target; unchanged
values hold through subsequent steps. Guide `initial` values are explicit, while
ordinary `anim.sequence` retains its rest-at-zero contract. Nest fixed joint frames
using `joints.frame`, preserving the pivots and axes. Never use teleporting or hidden
parts to bypass a blocked physical step.

The shared viewer provides guide selection, Play/Pause, Previous/Next (play the selected chapter), Replay step, Restart, and a progress slider. Ordinary playback respects chapter pauses; Play full tour explicitly plays continuously through them. Previous/Next play a chapter and stop at its end;
they do not instruct users to reverse a real-world procedure. Switching to
independent exploration stops the guide and restores the baseline before playing.

Read [manual-camera.md](manual-camera.md) for camera authoring, lead-in timing and visibility review. Deliver the generated GLB, its manifest, and the portable viewer files copied by `export_glb.py`. A generic
glTF viewer can play the entire clip without chapter metadata. The supplied viewer
fetches the manifest for instructions and chapter controls. Serve over localhost.

Validate metadata with `guide_schema.py` via the checker and delivery audit. Evidence
validation verifies nonempty source/locator fields; the author/reviewer must check
the actual referenced material. Render the guide storyboard and inspect every
chapter and transition. Motion samples include chapter boundaries and neighboring
subframes, but are still discrete collision tests. Caption quality, instructional
correctness and visual fidelity require review beyond a technical pass.
