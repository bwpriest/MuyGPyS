# Copyright 2021 Lawrence Livermore National Security, LLC and other MuyGPyS
# Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: MIT

import numpy as np

from absl.testing import absltest
from absl.testing import parameterized

from MuyGPyS.gp.distance import pairwise_distances, crosswise_distances
from MuyGPyS.gp.muygps import MuyGPS
from MuyGPyS.neighbors import NN_Wrapper
from MuyGPyS.testing.test_utils import (
    _make_gaussian_matrix,
    _make_gaussian_dict,
    _make_gaussian_data,
    _basic_nn_kwarg_options,
    _fast_nn_kwarg_options,
)


class GPInitTest(parameterized.TestCase):
    @parameterized.parameters(
        (k_kwargs, e, ss)
        for k_kwargs in (
            (
                "matern",
                {
                    "nu": {"val": 1.0},
                    "length_scale": {"val": 7.2},
                },
            ),
            (
                "rbf",
                {
                    "length_scale": {"val": 1.5},
                },
            ),
        )
        for e in (({"val": 1e-5},))
        for ss in ({"val": [1.0, 0.98]}, {"val": 1.0})
    )
    def test_bounds_defaults_init(self, k_kwargs, eps, sigma_sq):
        kern, kwargs = k_kwargs
        muygps = MuyGPS(kern=kern, eps=eps, sigma_sq=sigma_sq, **kwargs)
        for param in kwargs:
            self.assertEqual(
                kwargs[param]["val"],
                muygps.kernel.hyperparameters[param](),
            )
            self.assertEqual(
                "fixed",
                muygps.kernel.hyperparameters[param].get_bounds(),
            )
        self.assertEqual(eps["val"], muygps.eps())
        self.assertEqual("fixed", muygps.eps.get_bounds())
        if np.isscalar(sigma_sq["val"]):
            self.assertEqual(sigma_sq["val"], muygps.sigma_sq())
        else:
            self.assertSequenceAlmostEqual(sigma_sq["val"], muygps.sigma_sq())
        self.assertEqual("fixed", muygps.sigma_sq.get_bounds())

    @parameterized.parameters(
        (k_kwargs, e, ss)
        for k_kwargs in (
            (
                "matern",
                {
                    "nu": {"val": 1.0, "bounds": (1e-2, 5e4)},
                    "length_scale": {"val": 7.2, "bounds": (2e-5, 2e1)},
                },
            ),
            (
                "rbf",
                {
                    "length_scale": {"val": 1.5, "bounds": (1e-1, 1e2)},
                },
            ),
            (
                "matern",
                {
                    "nu": {"val": 1.0, "bounds": "fixed"},
                    "length_scale": {"val": 7.2, "bounds": "fixed"},
                },
            ),
            (
                "rbf",
                {
                    "length_scale": {"val": 1.5, "bounds": "fixed"},
                },
            ),
        )
        for e in (
            (
                {"val": 1e-5, "bounds": (1e-8, 1e-2)},
                {"val": 1e-5, "bounds": "fixed"},
            )
        )
        for ss in (
            (
                {"val": [1.0, 0.98], "bounds": (1e-8, 2.0)},
                {"val": [1.0, 0.98], "bounds": "fixed"},
            )
        )
    )
    def test_full_init(self, k_kwargs, eps, sigma_sq):
        kern, kwargs = k_kwargs
        muygps = MuyGPS(kern=kern, eps=eps, sigma_sq=sigma_sq, **kwargs)
        for param in kwargs:
            self.assertEqual(
                kwargs[param]["val"],
                muygps.kernel.hyperparameters[param](),
            )
            self.assertEqual(
                kwargs[param]["bounds"],
                muygps.kernel.hyperparameters[param].get_bounds(),
            )
        self.assertEqual(eps["val"], muygps.eps())
        self.assertEqual(eps["bounds"], muygps.eps.get_bounds())
        if np.isscalar(sigma_sq["val"]):
            self.assertEqual(sigma_sq["val"], muygps.sigma_sq())
        else:
            self.assertSequenceAlmostEqual(sigma_sq["val"], muygps.sigma_sq())
        self.assertEqual(sigma_sq["bounds"], muygps.sigma_sq.get_bounds())

    @parameterized.parameters(
        (k_kwargs, e, ss)
        for k_kwargs in (
            (
                "matern",
                {
                    "nu": {"val": -1.0, "bounds": (1e-2, 5e4)},
                    "length_scale": {"val": 7000.2, "bounds": (2e-5, 2e1)},
                },
            ),
            (
                "rbf",
                {
                    "length_scale": {"val": 1e-2, "bounds": (1e-1, 1e2)},
                },
            ),
        )
        for e in (
            (
                {"val": 1e-1, "bounds": (1e-8, 1e-2)},
                {"val": 1e-9, "bounds": (1e-8, 1e-2)},
            )
        )
        for ss in (
            (
                {"val": 2.1, "bounds": (1e-8, 2.0)},
                {"val": 1e-8, "bounds": (1e-7, 1.5)},
            )
        )
    )
    def test_oob_init(self, k_kwargs, eps, sigma_sq):
        kern, kwargs = k_kwargs
        with self.assertRaises(ValueError):
            muygps = MuyGPS(kern=kern, eps=eps, sigma_sq=sigma_sq, **kwargs)

    @parameterized.parameters(
        (k_kwargs, e, ss, 100)
        for k_kwargs in (
            (
                "matern",
                {
                    "nu": {"val": "sample", "bounds": (1e-2, 5e4)},
                    "length_scale": {"val": "sample", "bounds": (2e-5, 1e1)},
                },
            ),
            (
                "rbf",
                {
                    "length_scale": {"val": "sample", "bounds": (1e-1, 1e2)},
                },
            ),
            (
                "matern",
                {
                    "nu": {"val": "log_sample", "bounds": (1e-2, 5e4)},
                    "length_scale": {
                        "val": "log_sample",
                        "bounds": (2e-5, 1e1),
                    },
                },
            ),
            (
                "rbf",
                {
                    "length_scale": {
                        "val": "log_sample",
                        "bounds": (1e-1, 1e2),
                    },
                },
            ),
        )
        for e in (
            (
                {"val": "sample", "bounds": (1e-8, 1e-2)},
                {"val": "log_sample", "bounds": (1e-8, 1e-2)},
            )
        )
        for ss in (
            (
                {"val": "sample", "bounds": (1e-8, 2.0)},
                {"val": "log_sample", "bounds": (1e-7, 1.5)},
            )
        )
    )
    def test_sample_init(self, k_kwargs, eps, sigma_sq, reps):
        kern, kwargs = k_kwargs
        for _ in range(reps):
            muygps = MuyGPS(kern=kern, eps=eps, sigma_sq=sigma_sq, **kwargs)
            for param in kwargs:
                self._check_in_bounds(
                    kwargs[param]["bounds"],
                    muygps.kernel.hyperparameters[param],
                )
            self._check_in_bounds(eps["bounds"], muygps.eps)
            self._check_in_bounds(sigma_sq["bounds"], muygps.sigma_sq)

    def _check_in_bounds(self, given_bounds, param):
        bounds = param.get_bounds()
        self.assertEqual(given_bounds, bounds)
        self.assertGreaterEqual(param(), bounds[0])
        self.assertLessEqual(param(), bounds[1])


class GPMathTest(parameterized.TestCase):
    @parameterized.parameters(
        (
            (1000, 100, f, 10, nn_kwargs, k_kwargs)
            for f in [100, 1]
            for nn_kwargs in _basic_nn_kwarg_options
            for k_kwargs in (
                {
                    "kern": "matern",
                    "metric": "l2",
                    "eps": {"val": 1e-5},
                    "nu": {"val": 1.0},
                    "length_scale": {"val": 7.2},
                },
                {
                    "kern": "rbf",
                    "metric": "F2",
                    "eps": {"val": 1e-5},
                    "length_scale": {"val": 1.5},
                },
            )
        )
    )
    def test_tensor_shapes(
        self,
        train_count,
        test_count,
        feature_count,
        nn_count,
        nn_kwargs,
        k_kwargs,
    ):
        muygps = MuyGPS(**k_kwargs)

        # prepare data
        train = _make_gaussian_matrix(train_count, feature_count)
        test = _make_gaussian_matrix(test_count, feature_count)

        # neighbors and distances
        nbrs_lookup = NN_Wrapper(train, nn_count, **nn_kwargs)
        nn_indices, _ = nbrs_lookup.get_nns(test)
        indices = np.arange(test_count)
        nn_dists = crosswise_distances(
            test, train, indices, nn_indices, metric=muygps.kernel.metric
        )
        F2_dists = pairwise_distances(
            train, nn_indices, metric=muygps.kernel.metric
        )

        # make kernels
        K, Kcross = muygps.kernel(F2_dists), muygps.kernel(nn_dists)

        # do validation
        self.assertEqual(K.shape, (test_count, nn_count, nn_count))
        self.assertEqual(Kcross.shape, (test_count, nn_count))
        self.assertTrue(np.all(K >= 0.0))
        self.assertTrue(np.all(K <= 1.0))
        self.assertTrue(np.all(Kcross >= 0.0))
        self.assertTrue(np.all(Kcross <= 1.0))
        # # Check that kernels are positive semidefinite
        for i in range(K.shape[0]):
            eigvals = np.linalg.eigvals(K[i, :, :])
            self.assertTrue(
                np.all(np.logical_or(eigvals >= 0.0, np.isclose(eigvals, 0.0)))
            )

    @parameterized.parameters(
        (
            (1000, 100, f, r, 10, nn_kwargs, k_kwargs)
            # for f in [100]
            # for r in [5]
            # for nn_kwargs in _fast_nn_kwarg_options
            for f in [100, 1]
            for r in [5, 1]
            for nn_kwargs in _basic_nn_kwarg_options
            for k_kwargs in (
                {
                    "kern": "matern",
                    "metric": "l2",
                    "eps": {"val": 1e-5},
                    "nu": {"val": 1.0},
                    "length_scale": {"val": 7.2},
                },
                {
                    "kern": "rbf",
                    "metric": "F2",
                    "eps": {"val": 1e-5},
                    "length_scale": {"val": 1.5},
                },
            )
        )
    )
    def test_tensor_solve(
        self,
        train_count,
        test_count,
        feature_count,
        response_count,
        nn_count,
        nn_kwargs,
        k_kwargs,
    ):
        muygps = MuyGPS(**k_kwargs)

        # prepare data
        train, test = _make_gaussian_data(
            train_count, test_count, feature_count, response_count
        )

        # neighbors and distances
        nbrs_lookup = NN_Wrapper(train["input"], nn_count, **nn_kwargs)
        nn_indices, _ = nbrs_lookup.get_nns(test["input"])
        indices = np.arange(test_count)
        nn_dists = crosswise_distances(
            test["input"],
            train["input"],
            indices,
            nn_indices,
            metric=muygps.kernel.metric,
        )
        F2_dists = pairwise_distances(
            train["input"], nn_indices, metric=muygps.kernel.metric
        )

        # make kernels
        K, Kcross = muygps.kernel(F2_dists), muygps.kernel(nn_dists)
        # solve GP regression
        train_targets = train["output"][nn_indices]
        responses = muygps._compute_solve(K, Kcross, train_targets)

        # validate
        self.assertEqual(responses.shape, (test_count, response_count))
        for i in range(test_count):
            self.assertSequenceAlmostEqual(
                responses[i, :],
                Kcross[i, :]
                @ np.linalg.solve(
                    K[i, :, :] + muygps.eps() * np.eye(nn_count),
                    train["output"][nn_indices[i], :],
                ),
            )

    @parameterized.parameters(
        (
            (1000, 100, f, r, 10, nn_kwargs, k_kwargs)
            for f in [100, 1]
            for r in [10, 2, 1]
            for nn_kwargs in _basic_nn_kwarg_options
            # for f in [1]
            # for r in [10]
            # for nn_kwargs in _fast_nn_kwarg_options
            for k_kwargs in (
                {
                    "kern": "matern",
                    "metric": "l2",
                    "eps": {"val": 1e-5},
                    "nu": {"val": 1.0},
                    "length_scale": {"val": 7.2},
                },
                {
                    "kern": "rbf",
                    "metric": "F2",
                    "eps": {"val": 1e-5},
                    "length_scale": {"val": 1.5},
                },
            )
        )
    )
    def test_diagonal_variance(
        self,
        train_count,
        test_count,
        feature_count,
        response_count,
        nn_count,
        nn_kwargs,
        k_kwargs,
    ):
        muygps = MuyGPS(**k_kwargs)

        # prepare data
        train, test = _make_gaussian_data(
            train_count, test_count, feature_count, response_count
        )

        # neighbors and distances
        nbrs_lookup = NN_Wrapper(train["input"], nn_count, **nn_kwargs)
        nn_indices, _ = nbrs_lookup.get_nns(test["input"])
        indices = np.arange(test_count)
        nn_dists = crosswise_distances(
            test["input"],
            train["input"],
            indices,
            nn_indices,
            metric=muygps.kernel.metric,
        )
        F2_dists = pairwise_distances(
            train["input"], nn_indices, metric=muygps.kernel.metric
        )

        # make kernels and variance
        K, Kcross = muygps.kernel(F2_dists), muygps.kernel(nn_dists)
        diagonal_variance = muygps._compute_diagonal_variance(K, Kcross)

        # validate
        self.assertEqual(diagonal_variance.shape, (test_count,))
        for i in range(test_count):
            self.assertAlmostEqual(
                diagonal_variance[i],
                1.0
                - Kcross[i, :]
                @ np.linalg.solve(
                    K[i, :, :] + muygps.eps() * np.eye(nn_count),
                    Kcross[i, :],
                ),
            )
            self.assertGreater(diagonal_variance[i], 0.0)


class GPSigmaSqTest(parameterized.TestCase):
    @parameterized.parameters(
        (
            (1000, f, r, 10, nn_kwargs, k_kwargs)
            for f in [100, 1]
            for r in [10, 2, 1]
            for nn_kwargs in _basic_nn_kwarg_options
            # for f in [100]
            # for r in [10]
            # for nn_kwargs in _fast_nn_kwarg_options
            for k_kwargs in (
                {
                    "kern": "matern",
                    "metric": "l2",
                    "eps": {"val": 1e-5},
                    "nu": {"val": 1.0},
                    "length_scale": {"val": 7.2},
                },
                {
                    "kern": "rbf",
                    "metric": "F2",
                    "eps": {"val": 1e-5},
                    "length_scale": {"val": 1.5},
                },
            )
        )
    )
    def test_batch_sigma_sq_shapes(
        self,
        data_count,
        feature_count,
        response_count,
        nn_count,
        nn_kwargs,
        k_kwargs,
    ):
        sigma_sq = {"val": [1e0] * response_count}
        muygps = MuyGPS(sigma_sq=sigma_sq, **k_kwargs)

        # prepare data
        data = _make_gaussian_dict(data_count, feature_count, response_count)

        # neighbors and distances
        nbrs_lookup = NN_Wrapper(data["input"], nn_count, **nn_kwargs)
        indices = np.arange(data_count)
        nn_indices, _ = nbrs_lookup.get_batch_nns(indices)
        F2_dists = pairwise_distances(
            data["input"], nn_indices, metric=muygps.kernel.metric
        )

        K = muygps.kernel(F2_dists)
        muygps.sigma_sq_optim(K, nn_indices, data["output"])

        if response_count > 1:
            self.assertEqual(len(muygps.sigma_sq()), response_count)
            for i in range(response_count):
                sigmas = muygps._get_sigma_sq_series(
                    K, nn_indices, data["output"][:, i]
                )
                self.assertEqual(sigmas.shape, (data_count,))
                self.assertAlmostEqual(muygps.sigma_sq()[i], np.mean(sigmas), 5)
        else:
            sigmas = muygps._get_sigma_sq_series(
                K, nn_indices, data["output"][:, 0]
            )
            self.assertEqual(sigmas.shape, (data_count,))
            self.assertAlmostEqual(muygps.sigma_sq(), np.mean(sigmas), 5)


if __name__ == "__main__":
    absltest.main()
