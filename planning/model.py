"""NumPy reference implementation of the published browser model and world.

Inference uses float64 arithmetic over the original float32 weights to match
JavaScript Number. Model methods receive images/features, never simulator state.
"""
from dataclasses import dataclass
from itertools import product
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts/action_jepa'
PLANS = np.array(list(product([-1, 0, 1], repeat=3)), dtype=np.int64)
MARGIN, IMPULSE, MAX_SPEED, HIT = .08, .035, .14, .06


class RNG:
    """Exact Mulberry32 stream used by the JavaScript game."""
    def __init__(self, seed): self.state = int(seed) & 0xffffffff
    def __call__(self):
        self.state = (self.state + 0x6D2B79F5) & 0xffffffff
        t = ((self.state ^ (self.state >> 15)) * (1 | self.state)) & 0xffffffff
        t = (t ^ ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xffffffff)) & 0xffffffff)) & 0xffffffff
        return ((t ^ (t >> 14)) & 0xffffffff) / 4294967296


def seed_hash(text):
    value = 2166136261
    for unit in np.frombuffer(text.encode('utf-16le'), dtype='<u2'):
        value = ((value ^ int(unit)) * 16777619) & 0xffffffff
    return value


def tick(position, velocity):
    p, v = np.array(position, dtype=float) + velocity, np.array(velocity, dtype=float, copy=True)
    below, above = p < MARGIN, p > 1 - MARGIN
    p = np.where(below, 2 * MARGIN - p, np.where(above, 2 * (1 - MARGIN) - p, p))
    return p, np.where(below | above, -v, v)


def rollout(position, velocity, actions, impulse=IMPULSE):
    actions = np.asarray(actions)
    if actions.shape[-1] != 3 or not np.isin(actions, [-1, 0, 1]).all():
        raise ValueError('Expected three actions in {-1, 0, 1}')
    shape = np.broadcast_shapes(np.shape(position)[:-1], np.shape(velocity)[:-1], actions.shape[:-1])
    p = np.broadcast_to(position, shape + (2,)).copy().astype(float)
    v = np.broadcast_to(velocity, shape + (2,)).copy().astype(float)
    ends = []
    for index in range(3):
        v[..., 0] = np.clip(v[..., 0] + actions[..., index] * impulse, -MAX_SPEED, MAX_SPEED)
        for _ in range(2): p, v = tick(p, v)
        ends.append(p.copy())
    return np.stack(ends, axis=-2)


GRID = np.stack(np.meshgrid(np.arange(24) / 23, np.arange(24) / 23), axis=-1).reshape(576, 2)


def render(position, amplitude=1., noise=0., random=None):
    p = np.asarray(position)
    distance = ((GRID - p[..., None, :]) ** 2).sum(-1)
    image = np.asarray(amplitude)[..., None] * np.exp(-distance / (2 * .042 ** 2))
    if random is not None:
        # Consume values even at noise=0, matching the browser's RNG stream.
        image = image + noise * np.fromiter((random() for _ in range(image.size)), float).reshape(image.shape)
    return np.minimum(1., image)


def scenario(seed, noise=.03, impulse=IMPULSE):
    random = RNG(seed)
    p0 = np.array([.16 + .68 * random(), .16 + .68 * random()])
    v = np.array([.02 + .035 * random(), .02 + .035 * random()])
    v *= [1 if random() > .5 else -1, 1 if random() > .5 else -1]
    p1, v = tick(p0, v)
    chosen = PLANS[int(random() * 27)]
    destination = rollout(p1, v, chosen, impulse)[-1]
    goal = np.array([np.clip(destination[0] + (random() - .5) * .036, .08, .92), destination[1]])
    amplitude = .7 + .3 * random()
    frames = np.stack([render(p, amplitude, noise, random) for p in [p0, p1]])
    return dict(seed=int(seed), p0=p0, p1=p1, v=v, goal=goal, frames=frames,
                goal_frame=render(goal), noise=noise, impulse=impulse)


def load_arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {k: archive[k].astype(np.float64) for k in archive.files}


def linear(x, weights, name):
    return np.asarray(x) @ weights[name + '.weight'].T + weights[name + '.bias']


@dataclass
class Model:
    encoder: dict
    action: dict
    probe: dict

    def encode(self, images):
        x = np.maximum(0, linear(images, self.encoder, 'net.1'))
        x = np.maximum(0, linear(x, self.encoder, 'net.3'))
        return linear(x, self.encoder, 'net.5')

    def predict_z(self, context, actions):
        q = (np.asarray(context) - self.action['mean']) / self.action['scale']
        x = np.concatenate([q[..., 0, :], q[..., 1, :], q[..., 1, :] - q[..., 0, :], actions], axis=-1)
        x = np.maximum(0, linear(x, self.action, 'net.0'))
        x = np.maximum(0, linear(x, self.action, 'net.2'))
        x = linear(x, self.action, 'net.4').reshape(x.shape[:-1] + (3, 8))
        return (q[..., 1, None, :] + x) * self.action['scale'] + self.action['mean']

    def decode(self, z):
        x = (z - self.probe['mean']) / self.probe['scale']
        x = np.maximum(0, linear(x, self.probe, 'net.0'))
        x = np.maximum(0, linear(x, self.probe, 'net.2'))
        return 1 / (1 + np.exp(-np.clip(linear(x, self.probe, 'net.4'), -700, 700)))

    def rank(self, frames, goal_frame):
        z, goal = self.encode(frames), self.encode(goal_frame)
        shape = z.shape[:-2]
        context = np.broadcast_to(z[..., None, :, :], shape + (27, 2, 8))
        actions = np.broadcast_to(PLANS, shape + (27, 3))
        predicted = self.predict_z(context, actions)
        costs = (((predicted[..., -1, :] - goal[..., None, :]) / self.action['scale']) ** 2).mean(-1)
        return np.argmin(costs, axis=-1), costs, predicted


def load_model(predictor=None):
    return Model(load_arrays(ARTIFACTS / 'encoder.npz'),
                 load_arrays(predictor or ARTIFACTS / 'predictor.npz'),
                 load_arrays(ARTIFACTS / 'probe.npz'))
