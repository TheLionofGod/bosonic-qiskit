import math

import numpy as np
import qiskit
import qiskit.quantum_info
from qiskit.quantum_info import Statevector


from c2qa import CVCircuit

def flatten(l):
    return [item for sublist in l for item in sublist]

def cv_measure_fock(circuit,list_qumodes_to_sample:list, qmr_number:int=0):
    """Simulate the circuit with an appended binary search for boson number, and determine the Fock state of a set of qumodes.
    
    Returns the Fock state of the qumodes in list_qumodes_to_sample, in qumode register qmr_number.
    """
    # Count number of qubits in circuit so far
    num_qubits = len(flatten(circuit._qubit_regs))
    # Collect qumode register from circuit
    qmr = circuit.qmregs[qmr_number]
    # Add one ancilla qubits to the circuit per qumode to measure
    qbr_extra = qiskit.QuantumRegister(size=len(list_qumodes_to_sample), name="qbr_sampling")
    # Add classical bits to readout measurement results
    cbr_extra = qiskit.ClassicalRegister(len(list_qumodes_to_sample)*circuit.num_qubits_per_qumode, name="cbr_sampling")
    circuit.add_register(qbr_extra,cbr_extra)
    # Iterate over the qumodes
    qumode_counter=0
    for j in list_qumodes_to_sample:
        # Set the initial maximum Fock state
        max = circuit.cutoff
        # Iterate a number of time corresponding to the number of bits required to represent the maximum Fock state in binary (remove useless characters at the front)
        for iteration in range(len(bin(circuit.cutoff))-3):
            # Make sure the ancilla qubit is always reset to 0
            circuit.initialize('0',qbr_extra[qumode_counter])
            # Apply a circuit which flips the ancilla if the qumode occupation is odd etc. see (Curtis et al., PRA, 2021 and Wang et al.,  PRX, 2020)
            circuit.cv_c_pnr(max,qmr[list_qumodes_to_sample[j]],qbr_extra[qumode_counter])
            # Measure the qubit onto the classical bits (from left to right)
            classical_bit=circuit.num_qubits_per_qumode-1-iteration+(qumode_counter*circuit.num_qubits_per_qumode)
            circuit.measure(qbr_extra[qumode_counter],classical_bit)
            # Update the maximum value for the SNAP gate creation
            max = int(max/2)
        circuit.barrier()
        qumode_counter+=1
    # Simulate circuit with a single shot
    _, result = simulate(circuit, shots=1)
    # Return integer value of boson number occupation, converted from the bits which make up a binary number
    print(result.get_counts())
    full_set_of_binary = list(result.get_counts().keys())[0].encode('ascii')
    results_integers = np.zeros([len(list_qumodes_to_sample)])
    for j in range(len(list_qumodes_to_sample)):
        binary_number = full_set_of_binary[j*circuit.num_qubits_per_qumode:((j+1)*circuit.num_qubits_per_qumode)]
        print(binary_number)
        results_integers[-(j+1)] = int(binary_number,2)
    return results_integers

def stateread(
    stateop, numberofqubits, numberofmodes, cutoff, verbose=True, little_endian=False
):
    """Print values for states of qubits and qumodes using the result of a
    simulation of the statevector, e.g. using stateop, _ = c2qa.util.simulate(circuit).

    Returns the states of the qubits and the Fock states of the qumodes with respective amplitudes.
    """
    st = np.array(stateop)  # convert state to np.array
    amp_cv = []
    amp_qb = []
    state = []

    cutoff = 2**int(np.ceil(np.log2(cutoff))) # The cutoff needs to be a power of 2 for this code to work

    for i in range(len(st)):
        res = st[
            i
        ]  # go through vector element by element and find the positions of the non-zero elements with next if clause
        if np.abs(res) > 1e-10:
            pos = i  # position of amplitude (non-zero real)
            # print("position of non-zero real amplitude: ", pos, " res = ", res)
            sln = len(st)  # length of the state vector

            # Find the qubit states
            qbst = np.empty(numberofqubits, dtype="int")  # stores the qubit state
            iqb = 0  # counts up until the total number of qubits is reached

            # which half of the vector the amplitude is in is the state of the
            # first qubit because of how the kronecker product is made
            while iqb < numberofqubits:
                # if the amplitude is in the first half of the state vector or remaining statevector
                if (pos < sln / 2):
                    qbst[iqb] = int(0)  # then the qubit is in 0
                else:
                    # if the amplitude is in the second half then it is in 1
                    qbst[iqb] = int(1)

                    # if the amplitude is in the second half of the statevector,
                    # then to find out the state of the other qubits and cavities
                    # then we remove the first half of the statevector for simplicity
                    # because it corresponds to the qubit being in 0 which isn't the case.
                    pos = pos - (sln / 2)
                    # print("pos (sln/2)", pos, "sln ",sln)

                # only consider the part of the statevector corresponding to the qubit state which has just been discovered
                sln = (sln / 2)

                # up the qubit counter to start finding out the state of the next qubit
                iqb = (iqb + 1)
            amp_qb.append((qbst * (np.abs(res) ** 2)).tolist())

            # Find the qumode states
            qmst = np.empty(
                numberofmodes, dtype="int"
            )  # will contain the Fock state of each mode
            # print("qmst starting in ", qmst)
            iqm = 0  # counts up the number of modes
            # print("position is now: ",pos)
            while iqm < numberofmodes:
                # print("mode counter iqm ", iqm)
                # print("cutoff ", cutoff)
                # print("length of vector left to search: sln ", sln)

                # length of a division is the length of the statevector divided
                # by the cutoff of the hilbert space (which corresponds to the
                # number of fock states which a mode can have)
                lendiv = (sln / cutoff)
                # print("lendiv (sln/cutoff)", lendiv)
                val = pos / lendiv
                # print("rough estimate of the position of the non-zero element: val (pos/lendiv) ", val)
                fock = math.floor(val)
                # print("Fock st resulting position in Kronecker product (math.floor(val)) ", fock)
                qmst[iqm] = fock

                # remove a number of divisions to then search a subsection of the Kronecker product
                pos = pos - (fock * lendiv)
                # print("new position for next order of depth of Kronecker product/pos: (pos-(fock*lendiv)) ",pos)

                # New length of vector left to search
                sln = sln - ((cutoff - 1) * lendiv)
                # print("New length of vector left to search: sln (sln-((cutoff-1)*lendiv))", sln)
                iqm = iqm + 1
            amp_cv.append((qmst * (np.abs(res) ** 2)).tolist())

            state.append([qmst.tolist(), qbst.tolist(), res])

            if verbose:
                if little_endian:
                    qmstr = ["".join(str(item)) for item in qmst]
                    qbstr = ["".join(str(item)) for item in qbst]
                    print(
                        "qumodes: ",
                        "".join(qmstr),
                        " qubits: ",
                        "".join(qbstr),
                        "    with amplitude: {0:.3f} {1} i{2:.3f}".format(
                            res.real, "-" if res.imag < 0 else "+", abs(res.imag)
                        ),
                        "(little endian)",
                    )
                else:
                    qmstr = ["".join(str(item)) for item in qmst[::-1]]
                    qbstr = ["".join(str(item)) for item in qbst[::-1]]
                    print(
                        "qumodes: ",
                        "".join(qmstr),
                        " qubits: ",
                        "".join(qbstr),
                        "    with amplitude: {0:.3f} {1} i{2:.3f}".format(
                            res.real, "-" if res.imag < 0 else "+", abs(res.imag)
                        ),
                        "(big endian)",
                    )

    occupation_cv = [sum(i) for i in zip(*amp_cv)]
    occupation_qb = [sum(i) for i in zip(*amp_qb)]

    if not little_endian:
        for i in range(len(state)):
            state[i][0] = state[i][0][::-1]
            state[i][1] = state[i][1][::-1]
        occupation_cv = occupation_cv[::-1]
        occupation_qb = occupation_qb[::-1]

    return [occupation_cv, occupation_qb], state


def cv_fockcounts(counts, qubit_qumode_list, reverse_endianness=False):
    """Convert counts dictionary from Fock-basis binary representation into
    base-10 Fock basis (qubit measurements are left unchanged). Accepts a counts
    dict() as returned by job.result().get_counts() along with qubit_qumode_list,
    a list of Qubits and Qumodes passed into cv_measure(...).

     Returns counts dict()

     Args:
         counts: dict() of counts, as returned by job.result().get_counts() for
            a circuit which used cv_measure()
         qubit_qumode_list: List of qubits and qumodes measured. This list should
            be identical to that passed into cv_measure()

     Returns:
         A new counts dict() which lists measurement results for the qubits and
         qumodes in qubit_qumode_list in little endian order, with Fock-basis
         qumode measurements reported as a base-10 integer.
    """

    flat_list = []
    for el in qubit_qumode_list:
        if isinstance(el, list):
            flat_list += el
        else:
            flat_list += [el]

    newcounts = {}
    for key in counts:
        counter = len(key) - len(flat_list)
        if counter > 0:
            newkey = ("{0:0" + str(counter) + "}").format(0)
        else:
            newkey = ""
        for registerType in qubit_qumode_list[::-1]:
            if isinstance(registerType, list):
                newkey += str(int(key[counter:counter + len(registerType)], base=2))
                # newkey += str(key[counter:counter+len(registerType)])
                counter += len(registerType)
            else:
                newkey += key[counter]
                counter += 1
        if reverse_endianness:
            newcounts[newkey[::-1]] = counts[key]
        else:
            newcounts[newkey] = counts[key]

    return newcounts


def measure_all_xyz(circuit: qiskit.QuantumCircuit):
    """Use QuantumCircuit.measure_all() to measure all qubits in the X, Y, and Z basis.

    Returns state, result tuples each for the X, Y, and Z basis.

    Args:
        circuit (qiskit.QuantumCircuit): circuit to measure qubits one

    Returns:
        x,y,z state & result tuples: (state, result) tuples for each x,y,z measurements
    """

    # QuantumCircuit.measure_all(False) returns a copy of the circuit with measurement gates.
    circuit_z = circuit.measure_all(False)
    state_z, result_z = simulate(circuit_z)

    circuit_x = circuit.copy()
    for qubit in circuit_x.qubits:
        circuit_x.h(qubit)
    circuit_x.measure_all()  # Add measure gates in-place
    state_x, result_x = simulate(circuit_x)

    circuit_y = circuit.copy()
    for qubit in circuit_y.qubits:
        circuit_y.sdg(qubit)
        circuit_y.h(qubit)
    circuit_y.measure_all()  # Add measure gates in-place
    state_y, result_y = simulate(circuit_y)

    return (state_x, result_x), (state_y, result_y), (state_z, result_z)


def get_probabilities(result: qiskit.result.Result):
    """Calculate the probabilities for each of the result's counts.

    Args:
        result (qiskit.result.Result): QisKit result to calculate probabilities from

    Returns:
        dict: probablity dictionary of each state
    """
    shots = 0
    counts = result.get_counts()
    for count in counts:
        shots += counts[count]
    probs = {}
    for count in counts:
        probs[count] = counts[count] / shots

    return probs


def simulate(
    circuit: CVCircuit,
    shots: int = 1024,
    add_save_statevector: bool = True,
    conditional_state_vector: bool = False,
    per_shot_state_vector: bool = False,
    noise_model=None,
    noise_passes=None,
    max_parallel_threads: int = 0,
):
    """Convenience function to simulate using the given backend.

    Handles calling into QisKit to simulate circuit using defined simulator.

    Args:
        circuit (CVCircuit): circuit to simulate
        shots (int, optional): Number of simulation shots. Defaults to 1024.
        add_save_statevector (bool, optional): Set to True if a state_vector instruction
                                               should be added to the end of the circuit. Defaults to True.
        conditional_state_vector (bool, optional): Set to True if the saved state vector should be contional
                                                   (each state value gets its own state vector). Defaults to False.

    Returns:
        tuple: (state, result) tuple from simulation
    """

    # If this is false, the user must have already called save_statevector!
    if add_save_statevector:
        circuit.save_statevector(
            conditional=conditional_state_vector, pershot=per_shot_state_vector
        )

    # Run noise pass, if provided
    if noise_passes:
        if not isinstance(noise_passes, list):
            noise_passes = [noise_passes]

        for noise_pass in noise_passes:
            circuit_compiled = noise_pass(circuit)
    else:
        circuit_compiled = circuit

    # Transpile for simulator
    simulator = qiskit.providers.aer.AerSimulator()
    circuit_compiled = qiskit.transpile(circuit_compiled, simulator)

    # Run and get statevector
    result = simulator.run(
        circuit_compiled, shots=shots, max_parallel_threads=max_parallel_threads, noise_model=noise_model
    ).result()

    # The user may have added their own circuit.save_statevector
    state = None
    if len(result.results):
        try:
            if conditional_state_vector or per_shot_state_vector:
                # Will get a dictionary of state vectors, one for each classical register value
                state = result.data()["statevector"]
            else:
                state = Statevector(result.get_statevector(circuit_compiled))
        except Exception:
            state = None  # result.get_statevector() will fail if add_save_statevector is false

    if add_save_statevector:
        circuit.data.pop()  # Clean up by popping off the SaveStatevector instruction

    return state, result


def _find_cavity_indices(circuit: CVCircuit):
    """
    Return the indices of the cavities from the circuit

    I.e., the indices to the qubits representing the bosonic modes.
    """

    # Find indices of qubits representing qumodes
    qmargs = []
    for reg in circuit.qmregs:
        qmargs.extend(reg.qreg)

    # Trace over the qubits representing qumodes
    index = 0
    indices = []
    for qubit in circuit.qubits:
        if qubit in qmargs:
            indices.append(index)
        index += 1

    return indices


def _find_qubit_indices(circuit: CVCircuit):
    """
    Return the indices of the qubits from the circuit that are not in a QumodeRegister

    I.e., the indices to the qubits themselves, not the qubits representing the bosonic modes.
    """

    # Find indices of qubits representing qumodes
    qmargs = []
    for reg in circuit.qmregs:
        qmargs.extend(reg.qreg)

    # Trace over the qubits not representing qumodes
    index = 0
    indices = []
    for qubit in circuit.qubits:
        if qubit not in qmargs:
            indices.append(index)
        index += 1

    return indices


def trace_out_qumodes(circuit: CVCircuit, state_vector):
    """Return reduced density matrix of the qubits by tracing out the cavities of the CVCircuit from the given Fock state vector.

    Args:
        circuit (CVCircuit): circuit yielding the results to trace over
        state_vector (Statevector): simulation results to trace over

    Returns:
        DensityMatrix: density matrix of the qubits from a partial trace over the cavities
    """

    indices = _find_cavity_indices(circuit)

    return qiskit.quantum_info.partial_trace(state_vector, indices)


def trace_out_qubits(circuit: CVCircuit, state_vector):
    """Return reduced density matrix of the cavities by tracing out the all qubits of the CVCircuit from the given Fock state vector.

    Args:
        circuit (CVCircuit): circuit with results to trace (to find Qubit index)
        state_vector (Statevector or DensityMatrix): simulation results to trace over

    Returns:
        DensityMatrix: partial trace
    """

    indices = _find_qubit_indices(circuit)

    return qiskit.quantum_info.partial_trace(state_vector, indices)


def cv_partial_trace(circuit: CVCircuit, state_vector, qubits: list):
    """Return reduced density matrix over the given Qiskit Qubits. 
    
    First find the indices of the given Qubits, then call qiskit.quantum_info.partial_trace
    
    Args:
        circuit (CVCircuit): circuit with results to trace (to find Qubit index)
        state_vector (Statevector or DensityMatrix): simulation results to trace over
        qubits (list): list of Qiskit Qubit to trace over

    Returns:
        DensityMatrix: partial trace"""
    
    if not isinstance(qubits, list):
        qubits = [qubits]
    indices = circuit.get_qubit_indices(qubits)

    return qiskit.quantum_info.partial_trace(state_vector, indices)
