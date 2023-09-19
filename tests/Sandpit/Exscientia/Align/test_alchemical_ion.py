import pytest

import BioSimSpace.Sandpit.Exscientia as BSS
from BioSimSpace.Sandpit.Exscientia.Align._alch_ion import _mark_alchemical_ion

from tests.conftest import root_fp


@pytest.fixture
def system():
    mol = BSS.IO.readMolecules(
        [f"{root_fp}/input/ala.top", f"{root_fp}/input/ala.crd"]
    )[0]
    system = BSS.Solvent.tip3p(mol, ion_conc=0.15, shell=2 * BSS.Units.Length.nanometer)
    return system


@pytest.fixture
def alchemical_ion_system(system):
    ion = _mark_alchemical_ion(system[-1])
    system.updateMolecules(ion)
    return system


@pytest.mark.parametrize(
    "input_system,isalchem", [("system", False), ("alchemical_ion_system", True)]
)
def test_isAlchemicalIon(input_system, isalchem, request):
    system = request.getfixturevalue(input_system)
    assert system[-1].isAlchemicalIon() is isalchem

@pytest.mark.parametrize(
    "input_system,isalchem", [("system", None), ("alchemical_ion_system", True)]
)
def test_getAlchemicalIon(input_system, isalchem, request):
    system = request.getfixturevalue(input_system)
    ion = system.getAlchemicalIon()
    if isalchem is None:
        assert ion is None
    else:
        assert isinstance(ion, BSS._SireWrappers.)
    assert .isAlchemicalIon()
