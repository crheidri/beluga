import copy
import time

# from ._bvp import *
import numpy as np
from scipy.integrate import solve_bvp

from beluga.data_classes.trajectory import Trajectory
from beluga.solvers.bvp_solvers import BaseAlgorithm, BVPResult


# noinspection PyTypeChecker
class SPBVP(BaseAlgorithm):
    r"""
    Reduced dimensional sparse collocation for solving boundary value problems.

    +------------------------+-----------------+-----------------+
    | Valid kwargs           | Default Value   | Valid Values    |
    +========================+=================+=================+
    | max_nodes              | 1000            | > 2             |
    +========================+=================+=================+

    """

    def __init__(self, *args, **kwargs):
        BaseAlgorithm.__init__(self, *args, **kwargs)
        self.max_nodes = kwargs.get('max_nodes', 2000)

    def solve(self, solinit, **kwargs):

        solinit = copy.deepcopy(solinit)
        nstates = solinit.y.shape[1]

        nquads = 0

        def return_nil(*_, **__):
            return np.array([])

        if solinit.q.size > 0:
            nquads = solinit.q.shape[1]
        else:
            nquads = 0
            self.quadrature_function = return_nil

        ndyn = solinit.p.size
        nnondyn = solinit.nu.size

        empty_array = np.array([])

        if nquads == 0:
            # TODO: Try to vectorize
            def _fun(t, y, params=empty_array, const=solinit.k):
                return np.vstack([self.derivative_function(yi[:nstates], params[:ndyn], const) for yi in y.T]).T

            def _bc(ya, yb, params=empty_array, const=solinit.k):
                return self.boundarycondition_function(ya, yb, params[:ndyn], params[ndyn:ndyn + nnondyn], const)
        else:
            def _fun(t, y, params=empty_array, const=solinit.k):
                y = y.T
                o1 = np.vstack([self.derivative_function(yi[:nstates], params[:ndyn], const) for yi in y])
                o2 = np.vstack([self.quadrature_function(yi[:nstates], params[:ndyn], const) for yi in y])
                return np.hstack((o1, o2)).T

            def _bc(ya, yb, params=np.array([]), const=solinit.k):
                return self.boundarycondition_function(ya[:nstates], ya[nstates:nstates+nquads], yb[:nstates],
                                                       yb[nstates:nstates+nquads], params[:ndyn],
                                                       params[ndyn:ndyn+nnondyn], const)

        if self.derivative_function_jac is not None:
            def _fun_jac(t, y, params=np.array([]), const=solinit.k):
                y = y.T
                df_dy = np.zeros((y[0].size, y[0].size, t.size))
                df_dp = np.zeros((y[0].size, ndyn+nnondyn, t.size))

                for ii, yi in enumerate(y):
                    df_dy[:, :, ii], _df_dp = self.derivative_function_jac(yi, params[:ndyn], const)
                    if nstates > 1 and len(_df_dp.shape) == 1:
                        _df_dp = np.array([_df_dp]).T

                    df_dp[:, :, ii] = np.hstack((_df_dp, np.zeros((nstates, nnondyn))))

                if ndyn + nnondyn == 0:
                    return df_dy
                else:
                    return df_dy, df_dp
        else:
            _fun_jac = None

        if self.boundarycondition_function_jac is not None:
            if nquads > 0:
                def _bc_jac(ya, yb, params=np.array([]), const=solinit.k):
                    dbc_dya, dbc_dyb, dbc_dp = \
                        self.boundarycondition_function_jac(ya[:nstates], ya[nstates:nstates+nquads], yb[:nstates],
                                                            yb[nstates:nstates+nquads], params[:ndyn],
                                                            params[ndyn:ndyn+nnondyn], const)
                    return dbc_dya, dbc_dyb, dbc_dp
            else:
                def _bc_jac(ya, yb, params=np.array([]), const=solinit.k):
                    dbc_dya, dbc_dyb, dbc_dp = \
                        self.boundarycondition_function_jac(ya, yb, params[:ndyn], params[ndyn:ndyn+nnondyn], const)
                    return dbc_dya, dbc_dyb, dbc_dp
        else:
            _bc_jac = None

        if nquads > 0:
            comp_time_0 = time.time()
            opt = solve_bvp(_fun, _bc, solinit.t, np.hstack((solinit.y, solinit.q)).T,
                            np.hstack((solinit.p, solinit.nu)),
                            max_nodes=self.max_nodes, fun_jac=_fun_jac, bc_jac=_bc_jac)
            comp_time = time.time() - comp_time_0
        else:
            comp_time_0 = time.time()
            opt = solve_bvp(_fun, _bc, solinit.t, solinit.y.T,
                            np.hstack((solinit.p, solinit.nu)),
                            max_nodes=self.max_nodes, fun_jac=_fun_jac, bc_jac=_bc_jac)
            comp_time = time.time() - comp_time_0

        sol = copy.copy(solinit)
        sol.t = opt['x']
        sol.y = opt['y'].T[:, :nstates]
        sol.q = opt['y'].T[:, nstates:nstates+nquads]
        sol.lam = np.zeros_like(sol.y)
        if opt['p'] is not None:
            sol.p = opt['p'][:ndyn]
            sol.nu = opt['p'][ndyn:ndyn + nnondyn]
        else:
            sol.p = np.array([])
            sol.nu = np.array([])

        sol.converged = opt['success']
        sol.aux['comp_time'] = comp_time
        sol.aux['niter'] = opt['niter']

        out = BVPResult(sol=sol, success=opt['success'], message=opt['message'], rms_residuals=opt['rms_residuals'],
                        niter=opt['niter'])

        return out

    def close(self):
        pass
