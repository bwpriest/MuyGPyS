# Copyright 2021-2024 Lawrence Livermore National Security, LLC and other
# MuyGPyS Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: MIT


import MuyGPyS._src.math.numpy as np


def _kk_fn(
    exp_inv_scaled_sum_sq_diffs,
    sum_sq_diffs,
    prod_sq_diffs,
    sum_quad_diffs,
    length_scale=1.0,
):
    return 0.25 * (
        (
            8 * length_scale**2
            - 8 * length_scale * sum_sq_diffs
            + 2 * prod_sq_diffs
            + sum_quad_diffs
        )
        * exp_inv_scaled_sum_sq_diffs
        / length_scale**4
    )


def _kg1_fn(
    exp_inv_scaled_sum_sq_diffs,
    diff_xy_quad_diffs,
    diff_yx_sq_diffs,
    length_scale=1.0,
):
    return 0.25 * (
        (6 * length_scale * diff_yx_sq_diffs + diff_xy_quad_diffs)
        * exp_inv_scaled_sum_sq_diffs
        / length_scale**4
    )


def _kg2_fn(
    exp_inv_scaled_sum_sq_diffs,
    sum_sq_diffs,
    prod_diffs,
    length_scale=1.0,
):
    return (
        0.5
        * prod_diffs
        * (-6 * length_scale + sum_sq_diffs)
        * exp_inv_scaled_sum_sq_diffs
        / length_scale**4
    )


def _g1g1_fn(
    exp_inv_scaled_sum_sq_diffs,
    sum_sq_diffs,
    sum_quad_diffs,
    prod_sq_diffs,
    length_scale=1.0,
):
    return 0.25 * (
        (
            4 * length_scale**2
            - 4 * length_scale * sum_sq_diffs
            - 2 * prod_sq_diffs
            + sum_quad_diffs
        )
        * exp_inv_scaled_sum_sq_diffs
        / length_scale**4
    )


def _g1g2_fn(
    exp_inv_scaled_sum_sq_diffs,
    diff_xy_sq_diffs,
    prod_diffs,
    length_scale=1.0,
):
    return (
        0.5
        * prod_diffs
        * diff_xy_sq_diffs
        * exp_inv_scaled_sum_sq_diffs
        / length_scale**4
    )


def _g2g2_fn(
    exp_inv_scaled_sum_sq_diffs,
    sum_sq_diffs,
    prod_sq_diffs,
    length_scale=1.0,
):
    return (
        (length_scale**2 - length_scale * sum_sq_diffs + prod_sq_diffs)
        * exp_inv_scaled_sum_sq_diffs
        / length_scale**4
    )


# compute the full covariance matrix for convergence, shear1 and shear2
def _shear_33_fn(diffs, length_scale=1.0, **kwargs):
    assert diffs.ndim >= 3
    shape = diffs.shape[:-1]
    n = shape[-2]
    m = shape[-1]
    prefix = shape[:-2]
    new_shape = prefix + (3, n, 3, m)
    full_m = np.zeros(new_shape)

    # compute intermediate difference tensors once here
    prod_diffs = np.prod(diffs, axis=-1)
    sq_diffs = diffs**2
    quad_diffs = sq_diffs**2
    sum_sq_diffs = np.sum(sq_diffs, axis=-1)
    prod_sq_diffs = np.prod(sq_diffs, axis=-1)
    sum_quad_diffs = np.sum(quad_diffs, axis=-1)
    diff_yx_sq_diffs = sq_diffs[..., 1] - sq_diffs[..., 0]
    diff_xy_sq_diffs = sq_diffs[..., 0] - sq_diffs[..., 1]
    diff_xy_quad_diffs = quad_diffs[..., 0] - quad_diffs[..., 1]
    exp_inv_scaled_sum_sq_diffs = np.exp(-sum_sq_diffs / (2 * length_scale))

    full_m[..., 0, :, 0, :] = _kk_fn(
        exp_inv_scaled_sum_sq_diffs,
        sum_sq_diffs,
        prod_sq_diffs,
        sum_quad_diffs,
        length_scale,
    )  # (0, 0)
    full_m[..., 0, :, 1, :] = full_m[..., 1, :, 0, :] = _kg1_fn(
        exp_inv_scaled_sum_sq_diffs,
        diff_xy_quad_diffs,
        diff_yx_sq_diffs,
        length_scale,
    )  # (0, 1), (1, 0)
    full_m[..., 0, :, 2, :] = full_m[..., 2, :, 0, :] = _kg2_fn(
        exp_inv_scaled_sum_sq_diffs, sum_sq_diffs, prod_diffs, length_scale
    )  # (0, 2), (2, 0)
    full_m[..., 1, :, 1, :] = _g1g1_fn(
        exp_inv_scaled_sum_sq_diffs,
        sum_sq_diffs,
        sum_quad_diffs,
        prod_sq_diffs,
        length_scale,
    )  # (1, 1)
    full_m[..., 1, :, 2, :] = full_m[..., 2, :, 1, :] = _g1g2_fn(
        exp_inv_scaled_sum_sq_diffs,
        diff_xy_sq_diffs,
        prod_diffs,
        length_scale,
    )  # (1, 2), (2, 1)
    full_m[..., 2, :, 2, :] = _g2g2_fn(
        exp_inv_scaled_sum_sq_diffs,
        sum_sq_diffs,
        prod_sq_diffs,
        length_scale,
    )  # (2, 2)

    return np.squeeze(full_m)


# compute the full covariance matrix for shear1 and shear2 only
def _shear_Kin23_fn(diffs, length_scale=1.0, **kwargs):
    assert diffs.ndim >= 3
    shape = diffs.shape[:-1]
    n = shape[-2]
    m = shape[-1]
    prefix = shape[:-2]
    new_shape = prefix + (2, n, 2, m)
    full_m = np.zeros(new_shape)

    # compute intermediate difference tensors once here
    prod_diffs = np.prod(diffs, axis=-1)
    sq_diffs = diffs**2
    quad_diffs = sq_diffs**2
    sum_sq_diffs = np.sum(sq_diffs, axis=-1)
    prod_sq_diffs = np.prod(sq_diffs, axis=-1)
    sum_quad_diffs = np.sum(quad_diffs, axis=-1)
    diff_xy_sq_diffs = sq_diffs[..., 0] - sq_diffs[..., 1]
    exp_inv_scaled_sum_sq_diffs = np.exp(-sum_sq_diffs / (2 * length_scale))

    full_m[..., 0, :, 0, :] = _g1g1_fn(
        exp_inv_scaled_sum_sq_diffs,
        sum_sq_diffs,
        sum_quad_diffs,
        prod_sq_diffs,
        length_scale,
    )  # (0, 0)
    full_m[..., 0, :, 1, :] = full_m[..., 1, :, 0, :] = _g1g2_fn(
        exp_inv_scaled_sum_sq_diffs,
        diff_xy_sq_diffs,
        prod_diffs,
        length_scale,
    )  # (0, 1), (1, 0)
    full_m[..., 1, :, 1, :] = _g2g2_fn(
        exp_inv_scaled_sum_sq_diffs,
        sum_sq_diffs,
        prod_sq_diffs,
        length_scale,
    )  # (1, 1)

    return np.squeeze(full_m)


# compute the crosscovariance matrix relating shear1 and shear2 only
# observations to convergence, shear1 and shear2 predictions.
def _shear_Kcross23_fn(diffs, length_scale=1.0, **kwargs):
    assert diffs.ndim >= 3
    shape = diffs.shape[:-1]
    n = shape[-2]
    m = shape[-1]
    prefix = shape[:-2]
    new_shape = prefix + (2, n, 3, m)
    full_m = np.zeros(new_shape)

    # compute intermediate difference tensors once here
    prod_diffs = np.prod(diffs, axis=-1)
    sq_diffs = diffs**2
    quad_diffs = sq_diffs**2
    sum_sq_diffs = np.sum(sq_diffs, axis=-1)
    prod_sq_diffs = np.prod(sq_diffs, axis=-1)
    sum_quad_diffs = np.sum(quad_diffs, axis=-1)
    diff_yx_sq_diffs = sq_diffs[..., 1] - sq_diffs[..., 0]
    diff_xy_sq_diffs = sq_diffs[..., 0] - sq_diffs[..., 1]
    diff_xy_quad_diffs = quad_diffs[..., 0] - quad_diffs[..., 1]
    exp_inv_scaled_sum_sq_diffs = np.exp(-sum_sq_diffs / (2 * length_scale))

    full_m[..., 0, :, 0, :] = _kg1_fn(
        exp_inv_scaled_sum_sq_diffs,
        diff_xy_quad_diffs,
        diff_yx_sq_diffs,
        length_scale,
    )  # (0, 0)
    full_m[..., 1, :, 0, :] = _kg2_fn(
        exp_inv_scaled_sum_sq_diffs, sum_sq_diffs, prod_diffs, length_scale
    )  # (1, 0)
    full_m[..., 0, :, 1, :] = _g1g1_fn(
        exp_inv_scaled_sum_sq_diffs,
        sum_sq_diffs,
        sum_quad_diffs,
        prod_sq_diffs,
        length_scale,
    )  # (0, 1)
    full_m[..., 0, :, 2, :] = full_m[..., 1, :, 1, :] = _g1g2_fn(
        exp_inv_scaled_sum_sq_diffs,
        diff_xy_sq_diffs,
        prod_diffs,
        length_scale,
    )  # (0, 2), (1, 1)
    full_m[..., 1, :, 2, :] = _g2g2_fn(
        exp_inv_scaled_sum_sq_diffs,
        sum_sq_diffs,
        prod_sq_diffs,
        length_scale,
    )  # (1, 2)

    return np.squeeze(full_m)
