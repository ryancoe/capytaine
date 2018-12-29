#!/usr/bin/env python
# coding: utf-8
"""Tests for the mesh submodule: definition and transformation of collections of meshes and symmetric meshes."""

import pytest
import numpy as np

from capytaine import Disk, AxialSymmetry, HorizontalCylinder, TranslationalSymmetry
from capytaine.mesh.mesh import Mesh
from capytaine.mesh.meshes_collection import CollectionOfMeshes
from capytaine.geometric_bodies import Sphere


def test_collection_of_meshes():
    # Create some dummy meshes
    vertices = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=np.float)
    dummy_meshes = [Mesh(vertices, [[0, 1, 2, 3]])]
    for i in range(3):
        dummy_meshes.append(dummy_meshes[0].copy())
        dummy_meshes[i+1].translate_z(i+1)

    # A first collection from a list
    coll = CollectionOfMeshes(dummy_meshes[:2])
    assert coll.nb_submeshes == 2
    assert coll.nb_vertices == 8
    assert coll.nb_faces == 2
    assert coll[1].nb_faces == 1
    assert np.all(coll.faces_areas == np.asarray([1.0, 1.0]))
    assert np.all(coll.faces == np.asarray([[0, 1, 2, 3], [4, 5, 6, 7]]))
    assert np.all(coll.indices_of_mesh(1) == slice(1, 2))

    # A copy of the collection
    copy_coll = coll.copy()
    copy_coll.translate_x(1.0)  # Move
    assert copy_coll.nb_faces == 2
    assert np.all(copy_coll.vertices[:, 0] >= 1.0)  # Has moved

    # Another collection from an iterable
    other_coll = CollectionOfMeshes(iter(dummy_meshes))
    assert other_coll.nb_faces == 4
    assert np.all(other_coll.vertices[:, 0] <= 1.0)  # Did not move

    # A collection of collections
    big_coll = CollectionOfMeshes((copy_coll, other_coll))
    assert big_coll.nb_faces == 6
    assert big_coll.nb_submeshes == 2

    # Move one object in one of the sub-meshes
    copy_coll[1].translate_x(1.0)
    assert big_coll.vertices[:, 0].max() == 3.0

    # Merging the big collection
    merged = big_coll.merged()
    assert isinstance(merged, Mesh)


def test_collection():
    sphere = Sphere(name="foo", center=(0, 0, -2)).mesh
    other_sphere = Sphere(name="bar", center=(0, 0, 2)).mesh

    coll = CollectionOfMeshes([sphere, other_sphere], name="baz")
    assert str(coll) == "baz"
    assert repr(coll) == ("CollectionOfMeshes("
                          "(AxialSymmetry(Mesh(nb_vertices=20, nb_faces=10, name=slice_of_foo_mesh), name=foo_mesh), "
                          "AxialSymmetry(Mesh(nb_vertices=20, nb_faces=10, name=slice_of_bar_mesh), name=bar_mesh)), "
                          "name=baz)")

    coll2 = CollectionOfMeshes([sphere, other_sphere])
    assert repr(coll2) == ("CollectionOfMeshes("
                           "AxialSymmetry(Mesh(nb_vertices=20, nb_faces=10, name=slice_of_foo_mesh), name=foo_mesh), "
                           "AxialSymmetry(Mesh(nb_vertices=20, nb_faces=10, name=slice_of_bar_mesh), name=bar_mesh))")
    assert str(coll2) == repr(coll2)

    assert coll == coll2
    assert hash(coll) == hash(coll2)

    assert coll[0] == coll2[0]

    coll.tree_view()

    clipped_coll = coll.keep_immersed_part(inplace=False)
    assert len(clipped_coll) == 1
    merged = clipped_coll.merged()
    assert merged == sphere.merged()

    assert np.allclose(sphere.center_of_mass_of_nodes, sphere.merged().center_of_mass_of_nodes)
    assert np.allclose(sphere.diameter_of_nodes, sphere.merged().diameter_of_nodes)


def test_join_axisymmetric_disks():
    """Given two axisymmetric meshes with the same axis, build a new axisymmetric mesh combining the two."""
    disk1 = Disk(radius=1.0, center=(-1, 0, 0), resolution=(6, 6), axial_symmetry=True).mesh
    disk2 = Disk(radius=2.0, center=(1, 0, 0), resolution=(8, 6), axial_symmetry=True).mesh
    joined = disk1.join_meshes(disk2, name="two_disks")
    assert isinstance(joined, AxialSymmetry)
    joined.tree_view()

    disk3 = Disk(radius=1.0, center=(0, 0, 0), resolution=(6, 4), axial_symmetry=True).mesh
    with pytest.raises(AssertionError):
        disk1.join_meshes(disk3)


def test_join_translational_cylinders():
    """Given two meshes with the same translation symmetry, join them into a single mesh with the same symmetry."""
    mesh1 = HorizontalCylinder(length=10.0, radius=1.0, center=(0, 5, -5), clever=True, nr=0, ntheta=10, nx=10).mesh
    mesh2 = HorizontalCylinder(length=10.0, radius=2.0, center=(0, -5, -5), clever=True, nr=0, ntheta=10, nx=10).mesh
    joined = mesh1.join_meshes(mesh2)
    assert isinstance(joined, TranslationalSymmetry)