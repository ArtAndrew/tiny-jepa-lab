"""Run with: python -m unittest discover -s tests -v"""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import torch
from tinyjepa.core import Config, World, TinyJEPA, reflect, jepa_loss, variance_covariance, save_model, load_model


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)

    def setUp(self):
        torch.manual_seed(123)
        self.cfg = Config()
        self.batch = World(self.cfg, 123).sample(16)
        self.model = TinyJEPA(self.cfg)

    def test_generator_reproducible(self):
        a = World(self.cfg, 7).sample(8)
        b = World(self.cfg, 7).sample(8)
        self.assertTrue(torch.equal(a.context, b.context))
        self.assertTrue(torch.equal(a.positions, b.positions))

    def test_independent_seeds(self):
        a = World(self.cfg, 7).sample(8)
        b = World(self.cfg, 8).sample(8)
        self.assertFalse(torch.equal(a.context, b.context))

    def test_frame_shapes_and_ranges(self):
        b = self.batch
        self.assertEqual(tuple(b.context.shape), (16, 2, 24, 24))
        self.assertEqual(tuple(b.future.shape), (16, 24, 24))
        self.assertTrue(torch.all((b.context >= 0) & (b.context <= 1)))
        self.assertTrue(torch.all((b.positions >= .08-1e-6) & (b.positions <= .92+1e-6)))

    def test_reflection(self):
        result = reflect(torch.tensor([.08, .92, 1.02, -.02]), .08)
        self.assertTrue(torch.allclose(result, torch.tensor([.08, .92, .82, .18]), atol=1e-6))

    def test_neural_output_shape(self):
        p, z = self.model(self.batch.context, self.batch.horizon)
        self.assertEqual(tuple(p.shape), (16, 8))
        self.assertEqual(tuple(z.shape), (16, 2, 8))

    def test_no_future_leakage_into_prediction(self):
        a, _ = self.model(self.batch.context, self.batch.horizon)
        self.batch.future.normal_()
        self.batch.positions.normal_()
        b, _ = self.model(self.batch.context, self.batch.horizon)
        self.assertTrue(torch.equal(a, b))

    def test_teacher_stop_gradient(self):
        loss, _ = jepa_loss(self.model, self.batch.context, self.batch.future, self.batch.horizon)
        loss.backward()
        self.assertTrue(all(p.grad is None for p in self.model.teacher.parameters()))
        self.assertTrue(any(p.grad is not None and p.grad.abs().sum() > 0 for p in self.model.encoder.parameters()))
        self.assertTrue(any(p.grad is not None and p.grad.abs().sum() > 0 for p in self.model.predictor.parameters()))

    def test_ema_update(self):
        before = next(self.model.teacher.parameters()).detach().clone()
        with torch.no_grad():
            next(self.model.encoder.parameters()).add_(1.0)
        self.model.update_teacher()
        after = next(self.model.teacher.parameters()).detach()
        self.assertTrue(torch.allclose(after, before+.01, atol=1e-6))

    def test_constant_features_penalized(self):
        var, cov = variance_covariance(torch.zeros(16, 8))
        self.assertGreater(float(var), .98)
        self.assertEqual(float(cov), 0)

    def test_finite_optimizer_step(self):
        opt = torch.optim.Adam(self.model.parameters(), lr=1e-3)
        loss, stats = jepa_loss(self.model, self.batch.context, self.batch.future, self.batch.horizon)
        opt.zero_grad(); loss.backward(); opt.step(); self.model.update_teacher()
        self.assertTrue(torch.isfinite(loss))
        self.assertTrue(all(torch.isfinite(p).all() for p in self.model.parameters()))
        self.assertIn("prediction_mse", stats)

    def test_npz_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            save_model(self.model, temp)
            restored = load_model(temp)
            a, _ = self.model(self.batch.context, self.batch.horizon)
            b, _ = restored(self.batch.context, self.batch.horizon)
            self.assertTrue(torch.equal(a, b))

    def test_invalid_horizon(self):
        with self.assertRaises(ValueError):
            self.model(self.batch.context, torch.zeros(16, dtype=torch.long))

    def test_invalid_context(self):
        with self.assertRaises(ValueError):
            self.model(self.batch.future, self.batch.horizon)

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            Config(ema=1).validate()

    def test_parameter_count(self):
        self.assertEqual(self.model.inference_parameter_count(), 103888)


if __name__ == '__main__':
    unittest.main()
