import pytest

import BioSimSpace as BSS

from tests.conftest import url, has_amber


@pytest.mark.skipif(has_amber is False, reason="Requires AMBER to be installed.")
def test_makeCompatibleWith():
    # Load the original PDB file. In this representation the system contains
    # a single molecule with two chains. We parse with pdb4amber to ensure
    # that the file can be parsed with tLEaP.
    system = BSS.IO.readPDB(f"{url}/1jr5.pdb", pdb4amber=True)

    # Parameterise with ff14SB and return the molecule. The system that is
    # generated by tLEaP contains two molecules, each corresponding to one
    # of the chains in the original system. The properties from the new system
    # are mapped back into the existing single-molecule format to preserve
    # chain information.
    molecule = BSS.Parameters.ff14SB(system[0]).getMolecule()

    # Load in the two-molecule tLEaP system.
    tLEaP_system = BSS.IO.readMolecules([f"{url}/1jr5.crd", f"{url}/1jr5.top"])

    # Now perform single-point energy calculations using the two molecular
    # representations.

    # Create a single-step minimisation protocol.
    protocol = BSS.Protocol.Minimisation(steps=1)

    # Create a process for the single molecule representation.
    process0 = BSS.Process.Amber(molecule.toSystem(), protocol)

    # Create a process for the multi molecule representation.
    process1 = BSS.Process.Amber(tLEaP_system, protocol)

    # Run the processes and wait for them to finish.
    process0.start()
    process0.wait()
    process1.start()
    process1.wait()

    # Compare bond energies. (In kJ / mol)
    nrg0 = process0.getBondEnergy().kj_per_mol().value()
    nrg1 = process1.getBondEnergy().kj_per_mol().value()
    assert nrg0 == pytest.approx(nrg1, rel=1e-2)

    # Compare angle energies. (In kJ / mol)
    nrg0 = process0.getAngleEnergy().kj_per_mol().value()
    nrg1 = process1.getAngleEnergy().kj_per_mol().value()
    assert nrg0 == pytest.approx(nrg1, rel=1e-2)

    # Compare dihedral energies. (In kJ / mol)
    nrg0 = process0.getDihedralEnergy().kj_per_mol().value()
    nrg1 = process1.getDihedralEnergy().kj_per_mol().value()
    assert nrg0 == pytest.approx(nrg1, rel=1e-2)

    # Make sure we can load a system from the process for the single-molecule
    # representation. This maps the coordinates back into the original topology.
    new_system = process0.getSystem()


@pytest.mark.parametrize("ignore_waters", [False, True])
def test_hydrogen_mass_repartitioning(system, ignore_waters):
    # Work out the initial mass of the system.
    initial_mass = 0
    for molecule in system:
        for mass in molecule._sire_object.property("mass").toVector():
            initial_mass += mass.value()

    # Repartition the hydrogen mass.
    system.repartitionHydrogenMass(factor=4)

    # Work out the new mass of the system.
    final_mass = 0
    for molecule in system:
        for mass in molecule._sire_object.property("mass").toVector():
            final_mass += mass.value()

    # Assert the the masses are approximately the same.
    assert final_mass == pytest.approx(initial_mass)

    # Invert the repartitioning.
    system.repartitionHydrogenMass(factor=1 / 4)

    # Work out the new mass of the system.
    final_mass = 0
    for molecule in system:
        for mass in molecule._sire_object.property("mass").toVector():
            final_mass += mass.value()

    # Assert the the masses are approximately the same.
    assert final_mass == pytest.approx(initial_mass)


def test_extract(system):
    """Test the extract method."""

    # A list of atom indices to extract.
    idxs = [0, 1, 2, 3]

    # Extract the first molecule from the system.
    mol = system[0]

    # Extract the atoms.
    partial_mol = mol.extract(idxs)

    assert partial_mol.nAtoms() == 4

    # Make sure the numbers match.
    assert partial_mol.number() == mol.number()

    # Extract and renumber.
    partial_mol = mol.extract(idxs, renumber=True)

    # Make sure the numbers are different.
    assert partial_mol.number() != mol.number()
