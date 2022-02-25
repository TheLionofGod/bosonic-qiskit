import os
import sys

module_path = os.path.abspath(os.path.join("../.."))
if module_path not in sys.path:
    sys.path.append(module_path)

import numpy as np
import c2qa
import qiskit
import numpy as np
import c2qa.util as util


def eiht(circuit, qma, qmb, qb, m, g, dt):
    circuit.cv_cpbs(np.pi*dt, qmb, qma, qb)
    # circuit.cv_r(dt*m, qma)
    # circuit.cv_r(dt*m, qmb)
    circuit.rx(-g*dt, qb)
    return circuit

# choice variable decides whether to return the occupation of modes (0) or qubits (1)
def trotterise_Z2LGT(circuit, numberofmodes, numberofqubits, qmr, qbr, cutoff, N, m, g, dt):
    occs=[np.zeros((N,numberofmodes)),np.zeros((N,numberofqubits))]

    for i in range(numberofqubits):
        circuit.h(qbr[i]) # Inititialises the qubit to a plus state (so that pauli Z flips it)
    print("initial state ")
    stateop, _ = c2qa.util.simulate(circuit)
    util.stateread(stateop, qbr.size, numberofmodes, cutoff)

    for i in range(N):
        print("dt+1", i*dt)
        for j in range(0,numberofmodes-1,2):
            eiht(circuit, qmr[j+1], qmr[j], qbr[j], m, g, dt)
        for j in range(1,numberofmodes-1,2):
            eiht(circuit, qmr[j+1], qmr[j], qbr[j], m, g, dt)
        stateop, result = c2qa.util.simulate(circuit)
        occupation = util.stateread(stateop, qbr.size, numberofmodes, 4)
        occs[0][i]=np.array(list(occupation[0]))
        occs[1][i]=np.array(list(occupation[1]))

    return occs