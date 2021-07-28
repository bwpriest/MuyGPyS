# Copyright 2021 Lawrence Livermore National Security, LLC and other MuyGPyS
# Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: MIT

"""Hyperparameters and kernel functors

Defines kernel functors (inheriting :class:`MuyGPyS.gp.kernels.KernelFn`) that
transform crosswise distance matrices into cross-covariance matrices and 
pairwise distance matrices into covariance or kernel matrices. 

Hyperparameters are expected to be provided in `Dict` form with the keys `"val"`
and `"bounds"`. `"bounds"` is either a 2-tuple indicating a lower and upper 
optimization bound or the string `"fixed"`, which exempts the hyperparameter 
from optimization (`"fixed"` is the default behavior if `bounds` is 
unspecified). `"val"` is either a floating point value (within the range between 
the upper and lower bounds if specified). 

See the following example to initialize an :class:`MuyGPyS.gp.kernels.Matern` 
object. Other kernel functors are similar, but require different 
hyperparameters.

Example:
    >>> from MuyGPyS.gp.kernels import Matern
    >>> kern = Matern(
    ...         nu = {"val": "log_sample", "bounds": (0.1, 2.5)},
    ...         length_scale = {"val": 7.2},
    ...         metric = "l2",
    ... }

One uses a previously computed `pairwise_dists` tensor (see 
:func:`MuyGPyS.gp.distance.pairwise_distance`) to compute a kernel tensor whose 
second two dimensions contain square kernel matrices. Similarly, one uses a 
previously computed `crosswise_dists` matrix (see 
:func:`MuyGPyS.gp.distance.crosswise_distance`) to compute a cross-covariance 
matrix. See the following example, which assumes that you have already 
constructed the distance `numpy.nparrays` and the kernel `kern` as shown above. 

Example:
    >>> K = kern(pairwise_dists)
    >>> Kcross = kern(crosswise_dists) 
"""

import numpy as np

from typing import Dict, Optional, Tuple, Union

from scipy.special import gamma, kv


class Hyperparameter:
    """
    A MuyGPs kernel or model Hyperparameter.

    Hyperparameters are defined by a value and optimization bounds. Values must
    be scalar numeric types, and bounds are either a len == 2 iterable container
    whose elements are numeric scalars in increasing order, or the string
    `fixed`. If `bounds == "fixed"` (the default behavior), the hyperparameter
    value will remain fixed during optimization. `val` must remain within the
    range of the upper and lower bounds, if not `fixed`.

    Args:
        val:
            A scalar within the range of the upper and lower bounds (if given).
            val can also be the strings `"sample"` or `"log_sample"`, which will
            result in randomly sampling a value within the range given by the
            bounds.
        bounds:
            Iterable container of len 2 containing lower and upper bounds (in
            that order), or the string `"fixed"`.

    Raises:
        ValueError:
            Any `bounds` string other than `"fixed"` will produce an error.
        ValueError:
            A non-iterable non-string type for `bounds` will produce an
            error.
        ValueError:
            A `bounds` iterable of len other than 2 will produce an error.
        ValueError:
            Iterable `bounds` values of non-numeric types will produce an error.
        ValueError:
            A lower bound that is not less than an upper bound will produce
            an error.
        ValueError:
            `val == "sample" or val == "log_sample"` will produce an error
            if `self._bounds == "fixed"`.
        ValueError:
            Any string other than `"sample"` or `"log_sample"` will produce
            an error.
        ValueError:
            A `val` outside of the range specified by `self._bounds` will
            produce an error.
    """

    def __init__(
        self,
        val: Union[str, float],
        bounds: Union[str, Tuple[float, float]],
    ):
        """
        Initialize a hyperparameter.
        """
        self._set_bounds(bounds)
        self._set_val(val)

    def _set(
        self,
        val: Optional[Union[str, float]] = None,
        bounds: Optional[Union[str, Tuple[float, float]]] = None,
    ) -> None:
        """
        Reset hyperparameter value and/or bounds using keyword arguments.

        Args:
            val:
                A valid value or `"sample"` or `"log_sample"`.
            bounds:
                Iterable container of len 2 containing lower and upper bounds
                (in that order), or the string `"fixed"`.
        Raises:
            ValueError:
                Any `bounds` string other than `"fixed"` will produce an error.
            ValueError:
                A non-iterable non-string type for `bounds` will produce an
                error.
            ValueError:
                A `bounds` iterable of len other than 2 will produce an error.
            ValueError:
                Iterable `bounds` values of non-numeric types will produce an error.
            ValueError:
                A lower bound that is not less than an upper bound will produce
                an error.
            ValueError:
                `val == "sample" or val == "log_sample"` will produce an error
                if `self._bounds == "fixed"`.
            ValueError:
                Any string other than `"sample"` or `"log_sample"` will produce
                an error.
            ValueError:
                A `val` outside of the range specified by `self._bounds` will
                produce an error.
        """
        if bounds is not None:
            self._set_bounds(bounds)
        if val is not None:
            self._set_val(val)

    def _set_val(self, val: Union[str, float]) -> None:
        """
        Set hyperparameter value; sample if appropriate.

        Throws on out-of-range and other badness.

        Args:
            val:
                A valid value or the strings `"sample"` or `"log_sample"`.

        Raises:
            ValueError:
                `val == "sample" or val == "log_sample"` will produce an error
                if `bounds == "fixed"`.
            ValueError:
                Any `val` string other than `"sample"` or `"log_sample"` will
                produce an error.
            ValueError:
                A `val` outside of the range specified by `bounds` will
                produce an error.
        """
        if not isinstance(val, str):
            val = np.squeeze(val).astype(float)
        if self._bounds == "fixed":
            if np.isscalar(val) and (val == "sample" or val == "log_sample"):
                raise ValueError(
                    f"Must provide optimization bounds in order to sample a "
                    f"hyperparameter value."
                )
        else:
            # NOTE[bwp] Do we want to support the sampling of vector-valued
            # hyperparameters?
            if np.isscalar(val) and val == "sample":
                val = np.random.uniform(
                    low=self._bounds[0], high=self._bounds[1]
                )
            elif np.isscalar(val) and val == "log_sample":
                val = np.exp(
                    np.random.uniform(
                        low=np.log(self._bounds[0]),
                        high=np.log(self._bounds[1]),
                    )
                )
            elif np.isscalar(val) and val == "learn":
                pass
            elif np.isscalar(val) and isinstance(val, str):
                raise ValueError(
                    f"string hyperparameter value {val} is not supported."
                )
            else:
                any_below = np.any(
                    np.choose(val < self._bounds[0] - 1e-5, [False, True])
                )
                any_above = np.any(
                    np.choose(val > self._bounds[1] + 1e-5, [False, True])
                )
                if any_below == True:
                    raise ValueError(
                        f"Hyperparameter value {val} is lesser than the "
                        f"optimization lower bound {self._bounds[0]}"
                    )
                if any_above == True:
                    raise ValueError(
                        f"Hyperparameter value {val} is greater than the "
                        f"optimization upper bound {self._bounds[1]}"
                    )
        self._val = val

    def _set_bounds(
        self,
        bounds: Union[str, Tuple[float, float]],
    ) -> None:
        """
        Set hyperparameter bounds.

        Args:
            bounds:
                Iterable container of len 2 containing lower and upper bounds
                (in that order), or the string `"fixed"`.

        Raises:
            ValueError:
                Any string other than `"fixed"` will produce an error.
            ValueError:
                A non-iterable type will produce an error.
            ValueError:
                An iterable of len other than 2 will produce an error.
            ValueError:
                Iterable values of non-numeric types will produce an error.
            ValueError:
                A lower bound that is not less than an upper bound will produce
                an error.
        """
        if bounds != "fixed":
            if isinstance(bounds, str) is True:
                raise ValueError(f"Unknown bound option {bounds}.")
            if hasattr(bounds, "__iter__") is not True:
                raise ValueError(
                    f"Unknown bound optiom {bounds} of a non-iterable type "
                    f"{type(bounds)}."
                )
            if len(bounds) != 2:
                raise ValueError(
                    f"Provided hyperparameter optimization bounds have "
                    f"unsupported length {len(bounds)}."
                )
            if np.issubdtype(type(bounds[0]), np.number) is not True:
                raise ValueError(
                    f"Nonscalar {bounds[0]} of type {type(bounds[0])} is not a "
                    f"supported hyperparameter bound type."
                )
            if np.issubdtype(type(bounds[1]), np.number) is not True:
                raise ValueError(
                    f"Nonscalar {bounds[1]} of type {type(bounds[1])} is not a "
                    f"supported hyperparameter bound type."
                )
            if float(bounds[0]) > float(bounds[1]):
                raise ValueError(
                    f"Lower bound {bounds[0]} is not lesser than upper bound "
                    f"{bounds[1]}."
                )
        self._bounds = bounds

    def __call__(self) -> float:
        """
        Value accessor.

        Returns:
            The current value of the hyperparameter.
        """
        return self._val

    def get_bounds(self) -> Union[str, Tuple[float, float]]:
        """
        Bounds accessor.

        Returns:
            The string `"fixed"` or the lower and upper bound tuple.
        """
        return self._bounds


def _init_hyperparameter(
    val_def: Union[str, float],
    bounds_def: Union[str, Tuple[float, float]],
    **kwargs,
) -> Hyperparameter:
    """
    Initialize a hyperparameter given default values.

    Args:
        val:
            A valid value or `"sample"` or `"log_sample"`.
        bounds:
            Iterable container of len 2 containing lower and upper bounds (in
            that order), or the string `"fixed"`.
        kwargs:
            A hyperparameter dict including as subset of the keys `val` and
            `bounds`.
    """
    val = kwargs.get("val", val_def)
    bounds = kwargs.get("bounds", bounds_def)
    return Hyperparameter(val, bounds)


class KernelFn:
    """
    A kernel functor.

    Base class for kernel functors that include a hyperparameter Dict and a
    call mechanism.

    Args:
        kwargs:
            Ignored (by this base class) keyword arguments.
    """

    def __init__(self, **kwargs):
        """
        Initialize dict holding hyperparameters.
        """
        self.hyperparameters = dict()
        self.metric = ""

    def set_params(
        self,
        **kwargs,
    ) -> None:
        """
        Reset hyperparameters using hyperparameter dict(s).

        Args:
            kwargs:
                Hyperparameter kwargs.
        """
        for name in kwargs:
            self.hyperparameters[name]._set(**kwargs[name])

    def __call__(self, squared_dists: np.ndarray) -> np.ndarray:
        pass

    def __str__(self) -> str:
        """
        Print state of hyperparameter dict.

        Intended only for testing purposes.
        """
        ret = ""
        for p in self.hyperparameters:
            param = self.hyperparameters[p]
            ret += f"{p} : {param()} - {param.get_bounds()}\n"
        return ret[:-1]


class RBF(KernelFn):
    """
    The radial basis function (RBF) or squared-exponential kernel.

    The RBF kernel includes a single explicit length scale parameter
    :math:`\\ell>0`, and depends upon a distance function
    :math:`d(\\cdot, \\cdot)`.
    NOTE[bwp] We currently assume that the kernel is isotropic, so
    :math:`|\\ell| = 1`.

    The kernel is defined by

    .. math::
        K(x_i, x_j) = \\exp\\left(- \\frac{d(x_i, x_j)}{2\\ell^2}\\right).

    Typically, :math:`d(\\cdot,\\cdot)` is the squared Euclidean distance
    or second frequency moment of the difference of the operands.

    Args:
        length_scale:
            A hyperparameter dict defining the length_scale parameter.
        metric:
            The distance function to be used. Defaults to `"F2"`.
    """

    def __init__(
        self,
        length_scale: Dict[
            str, Union[str, float, Tuple[float, float]]
        ] = dict(),
        metric: Optional[str] = "F2",
    ):
        super().__init__()
        self.length_scale = _init_hyperparameter(1.0, "fixed", **length_scale)
        self.hyperparameters["length_scale"] = self.length_scale
        self.metric = metric

    def __call__(self, squared_dists: np.ndarray) -> np.ndarray:
        """
        Compute RBF kernel(s) from a distance matrix or tensor.

        Args:
            squared_dists:
                A matrix or tensor of pairwise distances (usually squared l2 or
                F2) of shape `(data_count, nn_count, nn_count)` or
                `(data_count, nn_count)`. In the tensor case, matrix diagonals
                along last two dimensions are expected to be 0.

        Returns:
            A cross-covariance matrix of shape `(data_count, nn_count)` or a
            tensor of shape `(data_count, nn_count, nn_count)` whose last two
            dimensions are kernel matrices.
        """
        return np.exp(-squared_dists / (2 * self.length_scale() ** 2))


class Matern(KernelFn):
    """
    The Màtern kernel.

    The Màtern kernel includes a length scale parameter :math:`\\ell>0` and an
    additional smoothness parameter :math:`\\nu>0`. :math:`\\nu` is inversely
    proportional to the smoothness of the resulting function. The Màtern kernel
    also depends upon a distance function :math:`d(\\cdot, \\cdot)`.
    As :math:`\\nu\\rightarrow\\infty`, the kernel becomes equivalent to
    the :class:`RBF` kernel. When :math:`\\nu = 1/2`, the Matérn kernel
    becomes identical to the absolute exponential kernel.
    Important intermediate values are
    :math:`\\nu=1.5` (once differentiable functions)
    and :math:`\\nu=2.5` (twice differentiable functions).
    NOTE[bwp] We currently assume that the kernel is isotropic, so
    :math:`|\\ell| = 1`.

    The kernel is defined by

    .. math::
         k(x_i, x_j) =  \\frac{1}{\\Gamma(\\nu)2^{\\nu-1}}\\Bigg(
         \\frac{\\sqrt{2\\nu}}{l} d(x_i , x_j )
         \\Bigg)^\\nu K_\\nu\\Bigg(
         \\frac{\\sqrt{2\\nu}}{l} d(x_i , x_j )\\Bigg),

    where :math:`K_{\\nu}(\\cdot)` is a modified Bessel function and
    :math:`\\Gamma(\\cdot)` is the gamma function.

    Typically, :math:`d(\\cdot,\\cdot)` is the Euclidean distance or
    :math:`\\ell_2` norm of the difference of the operands.

    Args:
        nu:
            A hyperparameter dict defining the length_scale parameter.
        length_scale:
            A hyperparameter dict defining the length_scale parameter.
        metric:
            The distance function to be used. Defaults to `"l2"`.
    """

    def __init__(
        self,
        nu: Dict[str, Union[str, float, Tuple[float, float]]] = dict(),
        length_scale: Dict[
            str, Union[str, float, Tuple[float, float]]
        ] = dict(),
        metric: Optional[str] = "l2",
    ):
        super().__init__()
        self.nu = _init_hyperparameter(1.0, "fixed", **nu)
        self.length_scale = _init_hyperparameter(1.0, "fixed", **length_scale)
        self.hyperparameters["nu"] = self.nu
        self.hyperparameters["length_scale"] = self.length_scale
        self.metric = metric

    def __call__(self, dists):
        """
        Compute Matern kernels from distance tensor.

        Takes inspiration from
        [scikit-learn](https://github.com/scikit-learn/scikit-learn/blob/95119c13a/sklearn/gaussian_process/kernels.py#L1529)

        Args:
            squared_dists:
                A matrix or tensor of pairwise distances (usually squared l2 or
                F2) of shape `(data_count, nn_count, nn_count)` or
                `(data_count, nn_count)`. In the tensor case, matrix diagonals
                along last two dimensions are expected to be 0.

        Returns:
            A cross-covariance matrix of shape `(data_count, nn_count)` or a
            tensor of shape `(data_count, nn_count, nn_count)` whose last two
            dimensions are kernel matrices.
        """
        nu = self.nu()
        # length_scale = self.length_scale()
        dists = dists / self.length_scale()
        if nu == 0.5:
            K = np.exp(-dists)
        elif nu == 1.5:
            K = dists * np.sqrt(3)
            K = (1.0 + K) * np.exp(-K)
        elif nu == 2.5:
            K = dists * np.sqrt(5)
            K = (1.0 + K + K ** 2 / 3.0) * np.exp(-K)
        elif nu == np.inf:
            K = np.exp(-(dists ** 2) / 2.0)
        else:
            K = dists
            K[K == 0.0] += np.finfo(float).eps
            tmp = np.sqrt(2 * nu) * K
            K.fill((2 ** (1.0 - nu)) / gamma(nu))
            K *= tmp ** nu
            K *= kv(nu, tmp)
        return K


def _get_kernel(kern: str, **kwargs) -> KernelFn:
    """
    Select and return an appropriate kernel functor based upon the passed
    parameters.

    Args:
        embed_method:
            The embedding method to be used. Current supports only `"matern"` and
            `"rbf"`.
        kwargs : dict
            Kernel parameters, possibly including hyperparameter dicts.

    Return:
        The appropriately initialized kernel functor.
    """
    if kern == "rbf":
        return RBF(**kwargs)
    elif kern == "matern":
        return Matern(**kwargs)
    else:
        raise ValueError(f"Kernel type {kern} is not supported!")
