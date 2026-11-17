# ORBIT: a tiny JEPA-inspired world model you can play against

Hi! I'm Andrey, an independent researcher and educator exploring JEPA and ways to explain world models through hands-on experiments. I built **ORBIT**, a small open-source browser game that turns action-conditioned prediction into something you can try yourself.

**[Play in your browser](https://artandrew.github.io/tiny-jepa-lab/)** · **[Code and notebooks](https://github.com/ArtAndrew/tiny-jepa-lab)**

A ball is already moving. You choose three left/no-push/right actions to reach a target. The neural planner sees two 24×24 images, predicts the latent outcomes of all 27 action sequences, and picks the one closest to the goal image. The simulator then shows what really happened. Coordinates and velocity are not inputs to the neural planner; a separate probe visualizes its predictions.

The new v0.7 release adds:

- **Quick play:** one round to understand the idea.
- **Challenge a friend:** share a link with the scene and your actions; scores are recomputed when it opens.
- **Find a weakness:** move the target or add image noise, then find a case where you hit and the model misses. The scene can be shared so others can reproduce the failure.

Inference runs locally without an AI API or sign-up. The MIT-licensed repository includes synthetic data generation, full training from random initialization, separate weights, runnable notebooks and tests. Explanations and controls are available in English, Russian and Simplified Chinese.

The current model achieved **74.45% hits on 3,072 synthetic scenes**. It was selected from three complete training runs using that same benchmark, so this is not an independent post-selection estimate. [Benchmark and limitations](https://github.com/ArtAndrew/tiny-jepa-lab/blob/main/BENCHMARK.md) · [Training from scratch](https://github.com/ArtAndrew/tiny-jepa-lab/blob/main/FROM_SCRATCH.md).

This is an independent JEPA-inspired educational toy, not an implementation of this repository's experiments or Meta's V-JEPA weights. I'm sharing it here because this community studies physical planning with predictive representations.

I'd welcome feedback on whether the game explains latent-space planning clearly, and which small controlled experiment would be most informative next: an unseen impulse strength, observation noise, or replanning after each action. Reproducible failure links are especially welcome.
