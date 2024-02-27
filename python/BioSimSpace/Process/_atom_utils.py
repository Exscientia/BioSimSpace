######################################################################
# BioSimSpace: Making biomolecular simulation a breeze!
#
# Copyright: 2017-2023
#
# Authors: Lester Hedges <lester.hedges@gmail.com>
#
# BioSimSpace is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BioSimSpace is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BioSimSpace. If not, see <http://www.gnu.org/licenses/>.
#####################################################################
__all__ = ["_AToMUtils"]
from .. import Protocol as _Protocol


class _AToMUtils:
    # Internal class for creating openmm forces within an AToM process.
    def __init__(self, protocol):
        # Check for proper typing
        if not isinstance(protocol, _Protocol.AToM):
            raise TypeError("Protocol must be a BioSimSpace.Protocol object")
        self.protocol = protocol
        self.data = self.protocol.getData()

    def getAlignmentConstants(self):
        if self.protocol._get_is_annealing_step():
            self.alignment_k_distance = self.protocol.getAnnealOptions()[
                "anneal_k_distance"
            ]
            self.alignment_k_theta = self.protocol.getAnnealOptions()["anneal_k_theta"]
            self.alignment_k_psi = self.protocol.getAnnealOptions()["anneal_k_psi"]
        else:
            self.alignment_k_distance = self.protocol.getAlignKfSep()
            self.alignment_k_theta = self.protocol.getAlignKTheta()
            self.alignment_k_psi = self.protocol.getAlignKPsi()

    def findAbsoluteCoreIndices(self):
        import numpy as np

        self.lig1_first_atomnum = self.data["first_ligand1_atom_index"]
        self.lig1_rigid_atoms = list(
            np.add(self.lig1_first_atomnum, self.data["ligand1_rigid_core"])
        )
        self.lig2_first_atomnum = self.data["first_ligand2_atom_index"]
        self.lig2_rigid_atoms = list(
            np.add(self.lig2_first_atomnum, self.data["ligand2_rigid_core"])
        )

    def findDisplacement(self):
        if not isinstance(self.data["displacement"], list):
            raise TypeError("Displacement must be a list")
        elif not all(isinstance(x, float) for x in self.data["displacement"]):
            raise TypeError("Displacement must be a list of floats")
        self.displacement = self.data["displacement"]

    def createAlignmentForce(self):
        # This force is the same in every lambda window
        self.getAlignmentConstants()
        self.findAbsoluteCoreIndices()

        output = "\n\n"
        output += "k_distance = {}\n".format(self.alignment_k_distance)
        output += "k_theta = {}\n".format(self.alignment_k_theta)
        output += "k_psi = {}\n".format(self.alignment_k_psi)
        output += "idxs_a = {}\n".format(self.lig1_rigid_atoms)
        output += "idxs_b = {}\n".format(self.lig2_rigid_atoms)
        output += "\n\n"

        output += 'distance_energy_fn = "0.5 * k * ((x1 - x2 - dx)^2 + (y1 - y2 - dy)^2 + (z1 - z2 - dz)^2);"\n'
        output += "distance_force = CustomCompoundBondForce(2, distance_energy_fn)\n"
        output += "distance_force.addPerBondParameter('k')\n"
        output += "distance_force.addPerBondParameter('dx')\n"
        output += "distance_force.addPerBondParameter('dy')\n"
        output += "distance_force.addPerBondParameter('dz')\n"

        output += """distance_parameters = [
        k_distance*(
            kilojoules_per_mole / nanometer**2
        ),
        displacement[0]*nanometer,
        displacement[1]*nanometer,
        displacement[2]*nanometer,
        ]\n"""

        output += (
            "distance_force.addBond((idxs_b[0], idxs_a[0]), distance_parameters)\n"
        )
        output += "system.addForce(distance_force)\n"
        output += "\n\n"

        output += """angle_energy_fn = (
        "0.5 * k * (1 - cos_theta);"
        ""
        "cos_theta = (dx_1 * dx_2 + dy_1 * dy_2 + dz_1 * dz_2) / (norm_1 * norm_2);"
        ""
        "norm_1 = sqrt(dx_1^2 + dy_1^2 + dz_1^2);"
        "dx_1 = x2 - x1; dy_1 = y2 - y1; dz_1 = z2 - z1;"
        ""
        "norm_2 = sqrt(dx_2^2 + dy_2^2 + dz_2^2);"
        "dx_2 = x4 - x3; dy_2 = y4 - y3; dz_2 = z4 - z3;"
        )\n"""
        output += "angle_force = CustomCompoundBondForce(4, angle_energy_fn)\n"
        output += 'angle_force.addPerBondParameter("k")\n'
        output += """angle_force.addBond(
        (idxs_b[0], idxs_b[1], idxs_a[0], idxs_a[1]),
        [k_theta*kilojoules_per_mole],
        )\n"""
        output += "system.addForce(angle_force)\n\n"

        output += """dihedral_energy_fn = (
        "0.5 * k * (1 - cos_phi);"
        ""
        "cos_phi = (v_x * w_x + v_y * w_y + v_z * w_z) / (norm_v * norm_w);"
        ""
        "norm_v = sqrt(v_x^2 + v_y^2 + v_z^2);"
        "v_x = dx_31 - dot_31 * dx_21 / norm_21;"
        "v_y = dy_31 - dot_31 * dy_21 / norm_21;"
        "v_z = dz_31 - dot_31 * dz_21 / norm_21;"
        ""
        "dot_31 = (dx_31 * dx_21 + dy_31 * dy_21 + dz_31 * dz_21) / norm_21;"
        "dx_31 = x3 - x1; dy_31 = y3 - y1; dz_31 = z3 - z1;"
        ""
        "norm_w = sqrt(w_x^2 + w_y^2 + w_z^2);"
        "w_x = dx_54 - dot_54 * dx_21 / norm_21;"
        "w_y = dy_54 - dot_54 * dy_21 / norm_21;"
        "w_z = dz_54 - dot_54 * dz_21 / norm_21;"
        ""
        "dot_54 =(dx_54 * dx_21 + dy_54 * dy_21 + dz_54 * dz_21) / norm_21;"
        "dx_54 = x5 - x4; dy_54 = y5 - y4; dz_54 = z5 - z4;"
        ""
        "norm_21 = sqrt(dx_21^2 + dy_21^2 + dz_21^2);"
        "dx_21 = x2 - x1; dy_21 = y2 - y1; dz_21 = z2 - z1;"
        )\n"""

        output += "dihedral_force = CustomCompoundBondForce(5, dihedral_energy_fn)\n"
        output += 'dihedral_force.addPerBondParameter("k")\n'
        output += """dihedral_force.addBond(
        (idxs_b[0], idxs_b[1], idxs_b[2], idxs_a[0], idxs_a[2]),
        [0.5 * k_psi * kilojoules_per_mole],
        )\n"""
        output += """dihedral_force.addBond(
        (idxs_a[0], idxs_a[1], idxs_a[2], idxs_b[0], idxs_b[2]),
        [0.5 * k_psi*kilojoules_per_mole],
        )\n"""
        output += "system.addForce(dihedral_force)\n\n"
        return output

    def getLigand1AtomsAsList(self):
        import numpy as np

        return list(
            np.arange(
                self.data["first_ligand1_atom_index"],
                self.data["last_ligand1_atom_index"] + 1,
            )
        )

    def getLigand2AtomsAsList(self):
        import numpy as np

        return list(
            np.arange(
                self.data["first_ligand2_atom_index"],
                self.data["last_ligand2_atom_index"] + 1,
            )
        )

    def createATMForce(
        self,
        index,
    ):
        """
        Create a string which can be added directly to an openmm script to add an ATM force to the system.

        Parameters
        ----------
        index : int
            Index of current window - used to set window-dependent variables.
        """
        self.findDisplacement()
        output = ""
        output += "#Parameters for ATM force\n"
        output += "lig1_atoms = {}\n".format(self.getLigand1AtomsAsList())
        output += "lig2_atoms = {}\n".format(self.getLigand2AtomsAsList())
        # Divide by 10 to convert to nm
        d = [round(x, 3) for x in self.displacement]
        output += "displacement = {}\n".format(d)
        output += "#BioSimSpace output is in angstrom, divide by 10 to convert to the expected units of nm\n"
        output += "displacement = [i/10.0 for i in displacement]\n"
        output += "lambda1 = {}\n".format(self.protocol.getLambda1()[index])
        output += "lambda2 = {}\n".format(self.protocol.getLambda2()[index])
        output += "alpha = {}\n".format(self.protocol.getAlpha()[index])
        output += "uh = {}\n".format(self.protocol.getuh()[index])
        output += "w0 = {}\n".format(self.protocol.getW0()[index])
        output += "direction = {}\n".format(self.protocol.getDirections()[index])
        output += "sc_Umax = {}\n".format(self.protocol.getSCUmax())
        output += "sc_U0 = {}\n".format(self.protocol.getSCU0())
        output += "sc_a = {}\n".format(self.protocol.getSCa())

        output += "\n\n #Define ATM force\n"
        output += """atm_force = ATMForce(
        lambda1,
        lambda2,
        alpha * kilojoules_per_mole,
        uh * kilojoules_per_mole,
        w0 * kilojoules_per_mole,
        sc_Umax * kilojoules_per_mole,
        sc_U0 * kilojoules_per_mole,
        sc_a,
        direction,
        )"""

        output += "\n\n #Add ATM force to system\n"
        output += "for _ in prm.topology.atoms():\n"
        output += "    atm_force.addParticle(Vec3(0.0,0.0,0.0))"
        output += "\n"
        # TODO: add offset - check convesion of a list to a Vec3
        # Assuming that offset is the 3-vector which deifnes the ligand displacement
        # need to convert displacement to nm
        output += "for i in lig1_atoms:\n"
        output += "    atm_force.setParticleParameters(i, Vec3(*displacement))\n"
        output += "for i in lig2_atoms:\n"
        output += "    atm_force.setParticleParameters(i, -Vec3(*displacement))\n"
        output += "\n"
        output += "nonbonded_force_id = [i for i, force in enumerate(system.getForces()) if isinstance(force, NonbondedForce)][0]\n"
        output += "nonbonded = copy.deepcopy(system.getForce(nonbonded_force_id))\n"
        output += "system.removeForce(nonbonded_force_id)\n"
        output += "atm_force.addForce(nonbonded)\n"
        output += "system.addForce(atm_force)\n"
        return output

    def createCOMRestraint(self):
        """
        Create a string containing the CM-CM restriants for two groups of atoms.
        In most cases these will be some combination of protein and ligand atoms.
        Constants for the force are set in the protocol."""
        # Groups contained within the constraint
        protein_com = self.data["protein_com_atoms"]
        lig1_com = self.data["ligand1_com_atoms"]
        lig2_com = self.data["ligand2_com_atoms"]
        # Constants for the force
        kf_cm = self.protocol.getCMKf()
        tol_cm = self.protocol.getCMTol()
        output = ""
        output += "protein_com = {}\n".format(protein_com)
        output += "lig1_com = {}\n".format(lig1_com)
        output += "lig2_com = {}\n".format(lig2_com)
        output += "# Constants for the CM-CM force in their input units\n"
        output += "kfcm = {} * kilocalorie_per_mole / angstrom**2\n".format(kf_cm)
        output += "tolcm = {} * angstrom \n".format(tol_cm)

        # Add expression for cm restraint
        output += """
        expr = "(kfcm/2)*step(d12-tolcm)*(d12-tolcm)^2 "
        expr += " ; d12 = sqrt((x1 - offx - x2)^2 + (y1 - offy - y2)^2 + (z1 - offz - z2)^2 ) ; "
        """
        output += "force_CMCM = CustomCentroidBondForce(2, expr)\n"
        output += "force_CMCM.addPerBondParameter('kfcm')\n"
        output += "force_CMCM.addPerBondParameter('tolcm')\n"
        output += "force_CMCM.addPerBondParameter('offx')\n"
        output += "force_CMCM.addPerBondParameter('offy')\n"
        output += "force_CMCM.addPerBondParameter('offz')\n"
        output += "system.addForce(force_CMCM)\n"
        output += "force_CMCM.addGroup(protein_com)\n"
        output += "force_CMCM.addGroup(lig1_com)\n"
        output += "force_CMCM.addGroup(lig2_com)\n"

        output += """parameters_free = (
        kfcm.value_unit(openmm.unit.kilojoules_per_mole / openmm.unit.nanometer**2),
        tolcm.value_in_unit(openmm.unit.nanometer),
        displacement[0],
        displacement[1],
        displacement[2],
        )"""

        output += """parameters_bound = (
        kfcm.value_unit(openmm.unit.kilojoules_per_mole / openmm.unit.nanometer**2),
        tolcm.value_in_unit(openmm.unit.nanometer),
        0.0,
        0.0,
        0.0,
        )"""

        output += "force_CMCM.addBond((0,1), parameters_bound)\n"
        output += "force_CMCM.addBond((0,2), parameters_free)\n"

        return output

    def createAnnealingProtocol(self):
        """
        Create a string which can be added directly to an openmm script to add an annealing protocol to the system.
        """
        options = self.protocol.getAnnealOptions().copy()
        anneal_runtime = options["runtime"]
        anneal_cycle_time = options["cycle_time"]
        num_cycles = anneal_runtime / anneal_cycle_time
        cycle_numsteps = anneal_cycle_time / self.protocol.getTimeStep()

        prot = self.protocol.getAnnealValues()
        # Find all entries whose keys contain "start" and create a dictionary of these entries
        # Also remove the word "start" from the key
        start = {k.replace("_start", ""): v for k, v in prot.items() if "start" in k}
        # Same for "end"
        end = {k.replace("_end", ""): v for k, v in prot.items() if "end" in k}
        # write protocol to output in dictionary format
        output = ""
        output += f"values_start = {start}\n"
        output += f"values_end = {end}\n"
        output += "increments = {\n"
        output += f"    key: (values_end[key] - values_start[key]) / {num_cycles}\n"
        output += "    for key in values_start.keys()\n"
        output += "}\n"
        # First set all values using the start values
        output += "for key in values_start.keys():\n"
        output += "    simulation.context.setParameter(key, values_start[key])\n"
        # Now perform the annealing in cycles
        output += f"for i in range({int(num_cycles)}):\n"
        output += f"    simulation.step({cycle_numsteps})\n"
        output += "    print(f'Cycle {i+1}')\n"
        if options["save_state"]:
            output += "    state = simulation.context.getState(getPositions=True, getVelocities=True)\n"
        output += "    for key in values_start.keys():\n"
        output += "        simulation.context.setParameter(key, simulation.context.getParameter(key) + increments[key])\n"
        # Now add post-annealing equilibration if set
        if options["post_anneal_eq_time"] is not None:
            output += "#post-annealing equilibration\n"
            output += "simulation.context.setParameter('lambda1', 0.5)\n"
            output += "simulation.context.setParameter('lambda2', 0.5)\n"
            output += f"simulation.step({int(options['post_anneal_eq_time']/self.protocol.getTimeStep())})\n"
        output += "simulation.saveState('openmm.xml')"
        return output
