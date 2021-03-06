""" front-end reader utilities
"""
import numpy
# import scipy.linalg
from qcelemental import constants as qcc
import automol

X = numpy.newaxis

EH2WAVENUM = qcc.conversion_factor("hartree", "wavenumber")


def rotational_constants(geo):
    """ get the rotational constants in atomic units

    (may want to convert to other units here)
    """
    cons = automol.geom.rotational_constants(geo, amu=True)
    return cons


def normal_coordinates(geo, hess, project=True):
    """ normal coordinates
    """
    norm_coos, _, _ = _frequency_analysis(geo, hess, project=project)
    return norm_coos


def harmonic_frequencies(geo, hess, project=True):
    """ harmonic frequencies (in cm^-1)

    (imaginary entries returned as negative)
    """
    _, freqs_re, freqs_im = _frequency_analysis(geo, hess, project=project)
    freqs = numpy.subtract(freqs_re, freqs_im)
    freqs = tuple(freqs)
    return freqs


def _frequency_analysis(geo, hess, project=True):
    """ harmonic frequency analysis
    """
    mw_hess = mass_weighted_hessian(geo, hess, project=project)
    # print(mw_hess)
    fcs, mw_norm_coos = numpy.linalg.eigh(mw_hess)

    conv = qcc.conversion_factor("hartree", "wavenumber")
    freqs = numpy.sqrt(numpy.complex_(fcs)) * conv
    freqs_im = numpy.imag(freqs)
    freqs_re = numpy.real(freqs)

    mw_vec = mass_weighting_vector(geo)
    norm_coos = mw_norm_coos
    norm_coos = _normalize_columns(mw_vec * mw_norm_coos)
    return norm_coos, freqs_re, freqs_im


def mass_weighted_hessian(geo, hess, project=True):
    """ translation/rotation-projected mass-weighted hessian
    """
    mw_vec = mass_weighting_vector(geo)
    mw_mat = numpy.outer((1. / mw_vec), (1. / mw_vec))
    mw_hess = numpy.multiply(hess, mw_mat)
    if project:
        dim = len(mw_vec)
        trans_norm_coos = translational_normal_coordinates(geo,
                                                           mass_weighted=True)
        rot_norm_coos = rotational_normal_coordinates(geo,
                                                      mass_weighted=True)
        # print(trans_norm_coos)
        # print(rot_norm_coos)
        tr_norm_coos = numpy.hstack([trans_norm_coos, rot_norm_coos])
        proj = numpy.eye(dim) - numpy.dot(tr_norm_coos, tr_norm_coos.T)
        # proj = scipy.linalg.orth(proj, rcond=0.5)
        mw_hess = numpy.dot(numpy.dot(proj.T, mw_hess), proj)

    mw_hess = tuple(map(tuple, mw_hess))
    return mw_hess


def translational_normal_coordinates(geo, axes=None, mass_weighted=False):
    """ translational normal coordinates
    """
    if axes is None:
        axes = numpy.eye(3)
    natms = len(automol.geom.symbols(geo))
    trans_norm_coos = numpy.zeros((3*natms, 3))
    for col_idx, axis in enumerate(axes):
        for atm_idx in range(natms):
            row_slc = slice(3*atm_idx, 3*(atm_idx+1))
            trans_norm_coos[row_slc, col_idx] = axis

    if mass_weighted:
        mw_vec = mass_weighting_vector(geo)
        trans_norm_coos = mw_vec[:, X] * trans_norm_coos

    trans_norm_coos = _normalize_columns(trans_norm_coos)
    return trans_norm_coos


def rotational_normal_coordinates(geo, axes=None, mass_weighted=False):
    """ rotational normal coordinates
    """
    if axes is None:
        axes = numpy.eye(3)
    xyzs = numpy.array(automol.geom.coordinates(geo))
    natms = len(xyzs)
    rot_norm_coos = numpy.zeros((3*natms, 3))
    for col_idx, axis in enumerate(axes):
        for atm_idx, xyz in enumerate(xyzs):
            row_slc = slice(3*atm_idx, 3*(atm_idx+1))
            rot_norm_coos[row_slc, col_idx] = numpy.cross(xyz, axis)

    if mass_weighted:
        mw_vec = mass_weighting_vector(geo)
        rot_norm_coos = mw_vec[:, X] * rot_norm_coos

    # for linear molecules aligned to an axis, one of these can be zero
    rot_norm_coo_vecs = []
    for rot_norm_coo in rot_norm_coos.T:
        if numpy.linalg.norm(rot_norm_coo) > 1e-5:
            rot_norm_coo_vecs.append(rot_norm_coo)

    rot_norm_coos = numpy.transpose(rot_norm_coo_vecs)
    return rot_norm_coos


def mass_weighting_vector(geo):
    """ mass-weighting vector
    """
    amas = automol.geom.masses(geo, amu=False)
    mw_vec = numpy.sqrt(numpy.repeat(amas, 3))
    return mw_vec


def _normalize_columns(mat):
    """normalize the columns of a matrix
    :param mat: matrix
    :type mat: numpy.ndarray
    :rtype: numpy.ndarray
    """
    norms = list(map(numpy.linalg.norm, numpy.transpose(mat)))
    return numpy.divide(mat, norms)


def _column_vector(vec):
    """form an n x 1 column vector, flattening if necessary
    :param vec: vector or array
    :type vec: numpy.ndarray
    :rtype: numpy.ndarray
    """
    return numpy.reshape(vec, (-1, 1))
