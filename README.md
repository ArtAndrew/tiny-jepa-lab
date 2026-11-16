# ORBIT — a world model you can play

**Can you guide a ball to the target better than a tiny neural network?**

[**Play now →**](https://artandrew.github.io/tiny-jepa-lab/) · [Играть по-русски](https://artandrew.github.io/tiny-jepa-lab/ru/) · [中文体验](https://artandrew.github.io/tiny-jepa-lab/zh/)

English · [Русский](README.ru.md) · [简体中文](README.zh-CN.md)

ORBIT is an **educational world-model demo presented as a browser game**. A small, pretrained, JEPA-inspired neural network predicts the effects of actions and uses those predictions to plan. Choose three actions and compare your result with its plan.

[![A real ORBIT replay: choose three actions, compare the two paths, and see the scores.](docs/assets/orbit-demo.gif)](https://artandrew.github.io/tiny-jepa-lab/)

*Illustrated replay generated from the actual game rules and trained model. One example round, not a benchmark or a screen recording.*

## What is a world model?

A world model learns from observations to predict how its environment will change. When those predictions account for actions, it can help answer **“What happens if I do this?”** before choosing a plan.

In ORBIT, the “world” is deliberately small: **a ball, walls, and a target**.

1. **Observe:** turn two images of the moving ball into compact numerical features.
2. **Predict:** estimate the effects of 27 possible three-action plans in feature space.
3. **Choose and test:** select the plan closest to the goal image, then let the simulator reveal what actually happens.

The predictor does not generate future video frames. Its forecast can be wrong — seeing those mistakes is part of the demo. This is an independent educational implementation inspired by JEPA, with its own trained weights and a narrow task; it does not run Meta's V-JEPA model.

## Play

Choose **Left**, **No push**, or **Right** for each of three actions, then launch your plan. Complete five daily rounds; a smaller distance to the target earns more points. In the playground, try different plans and add image noise to explore the model's mistakes.

- Runs locally in your browser; no account or external AI API is needed to play.
- Russian, English, and Simplified Chinese; light, dark, and automatic themes.
- Save a result card and challenge a friend on the same daily scenes.
- Optional public leaderboard: after five rounds, open the prepared GitHub form and click **Create**. Your GitHub username and actions become public; scores are recomputed automatically. A GitHub account is needed only for this step.

The leaderboard keeps your best accepted result for a day. Close the corresponding GitHub issue to withdraw it. Scores are checked; assisted or automated play is not detected.

## Explore or contribute

Found a confusing control or a model failure? [Open an issue](https://github.com/ArtAndrew/tiny-jepa-lab/issues/new) with the day, round, and chosen actions. Screenshots and translation improvements are welcome.

[Developer guide](DEVELOPMENT.md) · [Original experiment report (RU)](materials/ORBIT_RELEASE_REPORT_RU.md) · [Launch materials](promotion/README.md)

The original notebook is preserved as study material; its additional training modules are not included. See the developer guide for the current reproducibility limits.

By [Andrey Artishchev](https://artishev.com) · [MIT License](LICENSE)
