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

The browser runs the supplied v0.3 model, with exact tensors extracted into `artifacts/action_jepa/`. The source binary hash and each file's hash are in [provenance.json](artifacts/action_jepa/provenance.json). Loading uses `allow_pickle=False`.

The original training source, histories and separate checkpoints were recovered on 2026-11-17. All 17 supplied source hashes were verified; the EMA teacher, probe and action-predictor tensors exactly match the browser model. See [recovered source](ml/original-training/), [original numeric checkpoints](artifacts/original-training/) and [new independent runs](FROM_SCRATCH.md).

## Recovered visual pretraining

Two 24 × 24 images and a horizon of 1–4 steps feed a trainable encoder and temporal predictor (28 → 128 → 128 → 8; 21,256 parameters). The target is the future image's EMA-teacher embedding, with stop-gradient. The teacher is initialized from the random student and updated with EMA 0.99 after each optimizer step. Coordinates and velocities never enter the neural loss.

The objective is `10 × prediction MSE + 10 × variance penalty + covariance penalty`. Regularization uses the concatenated student features of both context frames and the future frame. The student and temporal predictor train for 2,400 steps with batch 128, AdamW 0.001, weight decay 0.0001 and gradient clipping at 5. The final checkpoint is retained. Synthetic trajectories are generated online, seed 42 in the reference run.

Downstream training uses the **frozen EMA teacher**. The display probe trains on 8,192 observed embeddings with coordinate supervision, 800 steps, Adam 0.003. The action predictor trains on 65,536 trajectories for 5,000 steps, with AdamW and cosine decay to 0.0001. Its checkpoint minimizes validation latent MSE on 2,048 separate trajectories. These recovered settings differ from the v0.4 reconstruction below.

All new temporal runs independently initialize the encoder, teacher, temporal predictor, probe and action predictor. A second experimental recipe, `planning/from_scratch.py`, uses same-state VICReg-style image pretraining. It is not the original temporal objective. Its weaker planning results are published as a comparison between complete recipes, not a controlled claim about one loss term.

## New v0.4 training recipe

`planning/training.py` is a newly implemented and executed recipe, not a recovered historical script. It keeps the original encoder frozen and initializes a new action predictor for each seed. The probe is excluded from training.

- 65,536 independent trajectories per training seed; 2,048 validation trajectories from seed 41002.
- Start position: uniform `[0.16,0.84]²`. Speed magnitude per axis: uniform `[0.02,0.055]`, independently signed.
- Three uniformly sampled actions; horizontal impulse 0.035; speed cap 0.14; two simulation ticks per action; reflecting walls at 0.08 and 0.92.
- Renderer: 24 × 24 Gaussian spot, sigma 0.042; trajectory amplitude uniform `[0.7,1.0]`; independent uniform additive noise `[0,0.03]` per pixel, clipped at 1.
- Two context images and three future images. Target features use the same frozen encoder; coordinates only drive the renderer.
- Mean/scale estimated from training context features only; scale floor 0.0001.
- AdamW, learning rate 0.001, weight decay 0.0001, batch 256, 5,000 steps. MSE of normalized future features; no coordinate/reward loss.
- Validate every 250 steps and at the end; save the minimum-validation-loss checkpoint. CPU, two threads, deterministic PyTorch algorithms requested.
- Three complete runs: seeds 31001, 31003, 31005. All outcomes, checkpoints, logs and configurations are committed, rather than only the best run.

## Evaluation and limitations

[BENCHMARK.md](BENCHMARK.md) reports fresh measurements of the released model and all three retrained predictors, with scene-level confidence intervals and separate training-seed variation. The exact physics oracle has privileged information; reachable goals are generated deliberately, explaining its 100% hit rate in this task.

Noise and changed impulse tests demonstrate sensitivity to observation and dynamics shifts. These selected shifts do not establish broad generalization. The model sees no gravity, moving targets, real camera images or physical objects. The glass photos explain an idea; they are not this model's predictions or training domain.

The gallery deliberately selects mistakes. It is useful for understanding individual failures, not estimating their frequency or proving why the network made a particular error. The decoded coordinates also depend on the separately trained probe; a prediction-display error can involve both predictor and probe.

## License and usage

The repository's MIT license covers its code and supplied model artifacts. No external model API is used at inference. The demo is intended for learning and small reproducible experiments. Public leaderboard validation verifies replay scores, not whether a player acted without automation.
