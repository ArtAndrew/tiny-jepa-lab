# Add ORBIT, an interactive JEPA-inspired world-model tutorial

Proposed entry in the Tutorial section:

- [ORBIT — a world model you can play](https://github.com/ArtAndrew/tiny-jepa-lab) — Interactive browser demo of JEPA-inspired action-conditioned planning, with human-vs-model challenges, reproducible failure examples, and full training-from-scratch code and notebooks. [Play](https://artandrew.github.io/tiny-jepa-lab/).

## Pull request description

I'd like to suggest ORBIT as an interactive educational resource in the Tutorial section. I maintain the project.

Players choose three actions for a moving ball and compare their plan with a small JEPA-inspired neural planner. The model observes two images, predicts the latent outcomes of 27 plans and selects the one closest to the goal representation. The demo runs locally in the browser without registration.

The repository includes the full visual-encoder and action-predictor training pipeline, synthetic data generation, separate weights, runnable notebooks, tests and benchmark reports. The new gameplay release adds one-round quick play, shareable friend challenges and a mode for finding reproducible model failures.

This is an independent educational implementation with a deliberately narrow synthetic world, not Meta's V-JEPA weights or a general-purpose world model.

- [Live demo](https://artandrew.github.io/tiny-jepa-lab/)
- [Training from scratch](https://github.com/ArtAndrew/tiny-jepa-lab/blob/main/FROM_SCRATCH.md)
- [Benchmark and selection caveats](https://github.com/ArtAndrew/tiny-jepa-lab/blob/main/BENCHMARK.md)

Happy to adjust the wording or placement to fit the list.
