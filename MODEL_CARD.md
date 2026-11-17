# ORBIT model card

**Purpose:** an educational, JEPA-inspired world-model demo for a tiny synthetic ball world. It predicts feature representations conditioned on actions. It is not Meta's I-JEPA/V-JEPA implementation, an LLM, a universal world model or a deployed robot controller.

## Components

| Component | Architecture | Parameters | Role |
|---|---|---:|---|
| Frozen visual encoder | 576 → 128 → 64 → 8, ReLU hidden layers | 82,632 | Encode each 24 × 24 grayscale observation |
| Action predictor | 27 → 128 → 128 → 24, ReLU hidden layers | 23,192 | Predict three future 8-dimensional feature vectors |
| Frozen coordinate probe | 8 → 64 → 64 → 2, ReLU then sigmoid | 4,866 | Visualize predicted locations; never choose the plan |

Total: 110,690 parameters, plus normalization buffers. The original weights are float32. Browser inference and the NumPy reference accumulate in float64; new PyTorch training uses float32.

Predictor input: normalized features `z0`, `z1`, their difference, and three actions (8 + 8 + 8 + 3 = 27 values). The network predicts three residual feature vectors relative to `z1`. The planner evaluates every sequence in `{-1,0,+1}³`, minimizing mean squared normalized feature distance from the final predicted features to the encoded goal image. Tie-breaking follows plan order.

Only the predictor's features and the goal image determine the plan. The exact physics and state are used by the simulator and privileged oracle for evaluation. Planning is open-loop: three actions are chosen before execution.

## Released model and provenance

**The v0.6 game runs `temporal-44`, trained entirely from scratch with encoder seed 44 and action seed 31005.** [Current performance and selection limits](BENCHMARK.md) · [Complete weights and logs](experiments/temporal-44/) · [Deployment record](source/model-release.json). It scored 74.45% on the 3,072-scene benchmark used to choose the best of three full runs.

The complete training source, configurations, logs and numeric checkpoints are available in this repository. Inference loads numeric arrays with `allow_pickle=False`.

## Recovered visual pretraining

Two 24 × 24 images and a horizon of 1–4 steps feed a trainable encoder and temporal predictor (28 → 128 → 128 → 8; 21,256 parameters). The target is the future image's EMA-teacher embedding, with stop-gradient. The teacher is initialized from the random student and updated with EMA 0.99 after each optimizer step. Coordinates and velocities never enter the neural loss.

The objective is `10 × prediction MSE + 10 × variance penalty + covariance penalty`. Regularization uses the concatenated student features of both context frames and the future frame. The student and temporal predictor train for 2,400 steps with batch 128, AdamW 0.001, weight decay 0.0001 and gradient clipping at 5. The final checkpoint is retained. Synthetic trajectories are generated online, seed 42 in the reference run.

Downstream training uses the **frozen EMA teacher**. The display probe trains on 8,192 observed embeddings with coordinate supervision, 800 steps, Adam 0.003. The action predictor trains on 65,536 trajectories for 5,000 steps, with AdamW and cosine decay to 0.0001. Its checkpoint minimizes validation latent MSE on 2,048 separate trajectories. See the exact deployed settings below.

All new temporal runs independently initialize the encoder, teacher, temporal predictor, probe and action predictor. A second experimental recipe, `planning/from_scratch.py`, uses same-state VICReg-style image pretraining. It is not the original temporal objective. Its weaker planning results are published as a comparison between complete recipes, not a controlled claim about one loss term.

## Current action-predictor training

The deployed run uses visual seed 44 and action seed 31005. It trains every component from random initialization and uses the frozen EMA teacher for both action prediction and the display probe.

- 65,536 independent training trajectories; 2,048 validation trajectories from seed 31006.
- Start position: uniform `[0.16,0.84]²`; signed speed magnitude per axis: uniform `[0.02,0.055]`.
- Three sampled horizontal pushes; impulse 0.035; speed cap 0.14; two simulation ticks per action; reflecting walls at 0.08 and 0.92.
- 24 × 24 Gaussian images, sigma 0.042; trajectory brightness 0.7–1.0; independent additive pixel noise 0–0.03, clipped at 1.
- Two context images and three future images; all target embeddings come from the frozen teacher. Coordinates only drive the renderer.
- Mean and sample standard deviation estimated across all five training-frame embeddings; scale floor 0.01.
- AdamW, initial learning rate 0.001 with cosine decay to 0.0001, weight decay 0.0001, batch 256, 5,000 steps, gradient clipping at 5.
- Loss: normalized future-feature MSE, with no coordinate or reward targets. Validation at step 1 and each 250 steps selects the checkpoint; the benchmark is not used for checkpoint selection within a run.
- Three full runs are published, with visual seeds 42, 43 and 44. The deployed run was subsequently chosen for its best normal-condition result on the shared benchmark. That selection must be considered when interpreting 74.45%.

## Evaluation and limitations

[BENCHMARK.md](BENCHMARK.md) reports the deployed model, with scene-level confidence intervals and separate training-seed variation. The exact physics oracle has privileged information; reachable goals are generated deliberately, explaining its 100% hit rate in this task.

Noise and changed impulse tests demonstrate sensitivity to observation and dynamics shifts. These selected shifts do not establish broad generalization. The model sees no gravity, moving targets, real camera images or physical objects. The glass photos explain an idea; they are not this model's predictions or training domain.

The gallery deliberately selects mistakes. It is useful for understanding individual failures, not estimating their frequency or proving why the network made a particular error. The decoded coordinates also depend on the separately trained probe; a prediction-display error can involve both predictor and probe.

## License and usage

The repository's MIT license covers its code and supplied model artifacts. No external model API is used at inference. The demo is intended for learning and small reproducible experiments. Public leaderboard validation verifies replay scores, not whether a player acted without automation.
