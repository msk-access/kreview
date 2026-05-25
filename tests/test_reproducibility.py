"""Tests for kreview.reproducibility — global seed utility."""

import os
import random

import numpy as np
import pytest


def _torch_available() -> bool:
    """Check if PyTorch is importable."""
    try:
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


class TestSeedEverything:
    """Validate seed_everything() behaviour."""

    def test_sets_python_random(self):
        """Python random module should produce deterministic output after seeding."""
        from kreview.reproducibility import seed_everything

        seed_everything(123)
        a = [random.random() for _ in range(5)]
        seed_everything(123)
        b = [random.random() for _ in range(5)]
        assert a == b, "Python random not deterministic after seed_everything()"

    def test_sets_pythonhashseed(self):
        """PYTHONHASHSEED env var should be set to the seed string."""
        from kreview.reproducibility import seed_everything

        seed_everything(99)
        assert os.environ.get("PYTHONHASHSEED") == "99"

    def test_does_not_set_numpy_global(self):
        """np.random global state must NOT be touched (local-only policy).

        We verify by checking that the numpy state tuple is unchanged
        after calling seed_everything().
        """
        from kreview.reproducibility import seed_everything

        # Record numpy state before
        state_before = np.random.get_state()[1].copy()

        seed_everything(42)

        # Numpy global state should be unchanged
        state_after = np.random.get_state()[1].copy()
        assert np.array_equal(state_before, state_after), (
            "seed_everything() must NOT set np.random.seed() — "
            "numpy randomness flows through local random_state params"
        )

    def test_returns_seed(self):
        """Function should return the seed that was set."""
        from kreview.reproducibility import seed_everything

        assert seed_everything(77) == 77

    @pytest.mark.skipif(
        not _torch_available(),
        reason="PyTorch not installed",
    )
    def test_sets_torch_seed(self):
        """torch.initial_seed() should match the provided seed."""
        import torch

        from kreview.reproducibility import seed_everything

        seed_everything(55)
        assert torch.initial_seed() == 55

    @pytest.mark.skipif(
        not _torch_available(),
        reason="PyTorch not installed",
    )
    def test_deterministic_true_disables_benchmark(self):
        """cudnn.benchmark should be False when deterministic=True."""
        import torch

        from kreview.reproducibility import seed_everything

        seed_everything(42, deterministic=True)
        assert torch.backends.cudnn.deterministic is True
        assert torch.backends.cudnn.benchmark is False

    @pytest.mark.skipif(
        not _torch_available(),
        reason="PyTorch not installed",
    )
    def test_deterministic_false_enables_benchmark(self):
        """cudnn.benchmark should be True when deterministic=False."""
        import torch

        from kreview.reproducibility import seed_everything

        seed_everything(42, deterministic=False)
        assert torch.backends.cudnn.deterministic is False
        assert torch.backends.cudnn.benchmark is True
