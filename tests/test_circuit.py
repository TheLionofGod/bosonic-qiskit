import c2qa
import pytest
import qiskit
import numpy


def test_no_registers():
    with pytest.raises(ValueError):
        c2qa.CVCircuit()


def test_only_quantumregister():
    with pytest.raises(ValueError):
        qr = qiskit.QuantumRegister(1)
        c2qa.CVCircuit(qr)


def test_only_qumoderegister():
    c2qa.CVCircuit(c2qa.QumodeRegister(1, 1))


def test_multiple_qumoderegisters():
    with pytest.warns(UserWarning):
        c2qa.CVCircuit(c2qa.QumodeRegister(1, 1), c2qa.QumodeRegister(1, 1))


def test_correct():
    c2qa.CVCircuit(qiskit.QuantumRegister(1), c2qa.QumodeRegister(1, 1))


def test_with_classical():
    c2qa.CVCircuit(
        qiskit.QuantumRegister(1),
        c2qa.QumodeRegister(1, 1),
        qiskit.ClassicalRegister(1),
    )


def test_with_initialize():
    number_of_modes = 5
    number_of_qubits = number_of_modes
    number_of_qubits_per_mode = 2

    qmr = c2qa.QumodeRegister(
        num_qumodes=number_of_modes, num_qubits_per_qumode=number_of_qubits_per_mode
    )
    qbr = qiskit.QuantumRegister(size=number_of_qubits)
    cbr = qiskit.ClassicalRegister(size=1)
    circuit = c2qa.CVCircuit(qmr, qbr, cbr)

    sm = [0, 0, 1, 0, 0]
    for i in range(qmr.num_qumodes):
        circuit.cv_initialize(sm[i], qmr[i])

    circuit.initialize(numpy.array([0, 1]), qbr[0])

    state, result = c2qa.util.simulate(circuit)
    assert result.success


def test_with_delay(capsys):
    with capsys.disabled():
        number_of_modes = 1
        number_of_qubits = 1
        number_of_qubits_per_mode = 2

        qmr = c2qa.QumodeRegister(
            num_qumodes=number_of_modes, num_qubits_per_qumode=number_of_qubits_per_mode
        )
        qbr = qiskit.QuantumRegister(size=number_of_qubits)
        circuit = c2qa.CVCircuit(qmr, qbr)

        circuit.delay(100)
        circuit.cv_d(1, qmr[0])

        state, result = c2qa.util.simulate(circuit)
        assert result.success


def test_get_qubit_indices(capsys):
    with capsys.disabled():
        number_of_modes = 2
        number_of_qubits = 2
        number_of_qubits_per_mode = 2

        qmr = c2qa.QumodeRegister(
            num_qumodes=number_of_modes, num_qubits_per_qumode=number_of_qubits_per_mode
        )
        qbr = qiskit.QuantumRegister(size=number_of_qubits)
        cbr = qiskit.ClassicalRegister(size=1)
        circuit = c2qa.CVCircuit(qmr, qbr, cbr)  

        indices = circuit.get_qubit_indices([qmr[1]])
        print(f"qmr[1] indices = {indices}")
        assert indices == [2, 3]

        indices = circuit.get_qubit_indices([qmr[0]])
        print(f"qmr[0] indices = {indices}")
        assert indices == [0, 1]

        indices = circuit.get_qubit_indices([qbr[1]])
        print(f"qbr[1] indices = {indices}")
        assert indices == [5]

        indices = circuit.get_qubit_indices([qbr[0]])
        print(f"qbr[0] indices = {indices}")
        assert indices == [4]