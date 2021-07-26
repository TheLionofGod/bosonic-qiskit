import numpy as np
from qiskit.extensions.unitary import UnitaryGate
from qiskit.quantum_info import Operator
import scipy.sparse
import scipy.sparse.linalg
from scipy.sparse import csr_matrix, block_diag


class ParameterizedOperator(Operator):
    def __init__(self, op_func, *params):
        super().__init__(op_func(*params).toarray())

        self.op_func = op_func
        self.params = params

    def calculate_matrix(self, current_step: int = 1, total_steps: int = 1):
        param_fraction = current_step / total_steps

        values = []
        for param in self.params:
            values.append(param * param_fraction)

        values = tuple(values)

        return self.op_func(*values).toarray()


class CVGate(UnitaryGate):
    def __init__(self, data, label=None):
        super().__init__(data, label)

        self.op = data


class CVOperators:
    def __init__(self, cutoff: int, num_qumodes: int):
        # Annihilation operator
        data = np.sqrt(range(cutoff))
        self.a = scipy.sparse.spdiags(data=data, diags=[1], m=len(data), n=len(data))

        # Creation operator
        self.a_dag = self.a.conjugate().transpose()

        # Number operator
        # self.N = scipy.sparse.matmul(self.a_dag, self.a)
        self.N = self.a_dag * self.a

        # Identity
        self.id = scipy.sparse.eye(cutoff)

        # 2-qumodes operators
        if num_qumodes > 1:
            eye = scipy.sparse.eye(cutoff)
            self.a1 = scipy.sparse.kron(self.a, eye)
            self.a2 = scipy.sparse.kron(eye, self.a)
            self.a1_dag = self.a1.conjugate().transpose()
            self.a2_dag = self.a2.conjugate().transpose()
            self.id = scipy.sparse.kron(eye, eye)
            self.sbSz= (1/2)*(self.a1_dag*self.a1-self.a2_dag*self.a2)

    def bs(self, g):
        """Two-mode beam splitter opertor"""
        # a12dag = scipy.sparse.matmul(self.a1, self.a2_dag)
        # a1dag2 = scipy.sparse.matmul(self.a1_dag, self.a2)
        a12dag = self.a1 * self.a2_dag
        a1dag2 = self.a1_dag * self.a2

        # FIXME -- See Steve 5.4
        #   phi as g(t)
        #   - as +, but QisKit validates that not being unitary
        arg = (g * -1j * a12dag) - (np.conjugate(g * -1j) * a1dag2)

        return scipy.sparse.linalg.expm(arg)

    def d(self, alpha):
        """Displacement operator"""
        arg = (alpha * self.a_dag) - (np.conjugate(alpha) * self.a)

        return scipy.sparse.linalg.expm(arg)

    def r(self, theta):
        """Phase space rotation operator"""
        arg = 1j * theta * self.N

        return scipy.sparse.linalg.expm(arg)

    def s(self, zeta):
        """Single-mode squeezing operator"""
        # a_sqr = scipy.sparse.matmul(self.a, self.a)
        # a_dag_sqr = scipy.sparse.matmul(self.a_dag, self.a_dag)
        a_sqr = self.a * self.a
        a_dag_sqr = self.a_dag * self.a_dag
        arg = 0.5 * ((np.conjugate(zeta) * a_sqr) - (zeta * a_dag_sqr))

        return scipy.sparse.linalg.expm(arg)

    def s2(self, g):
        """Two-mode squeezing operator"""
        # a12_dag = scipy.sparse.matmul(self.a1_dag, self.a2_dag)
        # a12 = scipy.sparse.matmul(self.a1, self.a2)
        a12_dag = self.a1_dag * self.a2_dag
        a12 = self.a1 * self.a2

        # FIXME -- See Steve 5.7
        #   zeta as g(t)
        #   use of imaginary, but QisKit validates that is not unitary
        arg = (np.conjugate(g) * a12_dag) - (g * a12)

        return scipy.sparse.linalg.expm(arg)

    def aklt(self):
        xQB = (1 / 2) * np.array([[0, 1], [1, 0]])
        yQB = (1 / 2) * np.array([[0, -1j], [1j, 0]])
        zQB = (1 / 2) * np.array([[1, 0], [0, -1]])
        pQB = 2*(xQB + 1j * yQB)
        mQB = 2*(xQB - 1j * yQB)

        term1 = (1/2)*(scipy.sparse.kron(self.a1_dag*self.a2, pQB)+scipy.sparse.kron(self.a1*self.a2_dag, mQB))
        term2 = -(1/2)*scipy.sparse.kron(self.id,zQB)

        tl = (1 + (1 / np.sqrt(3))) * (self.sbSz * self.sbSz - self.sbSz)
        br = (1 - (1 / np.sqrt(3))) * (self.sbSz * self.sbSz + self.sbSz)

        ctilde = (1/2)*block_diag((tl, br))

        return term1 + term2 + ctilde

    def bs2m1q(self):
        eyeqb=scipy.sparse.eye(2)
        # eyeQB = np.array([[1, 0], [0, 1]])

        a12dag = scipy.sparse.kron(self.a1*self.a2_dag, eyeqb)
        a1dag2 = scipy.sparse.kron(self.a1_dag*self.a2, eyeqb)
        arg = (-1j * a12dag) - (np.conjugate(-1j) * a1dag2)

        return scipy.sparse.linalg.expm(arg)

        # bin
        # Ctilde = csr_matrix([[0, 0, 0, 0, 0, 0],
        #                      [0, 0, 0, 0, 0, 0],
        #                      [0, 0, (1 + (1 / np.sqrt(3))), 0, 0, 0],
        #                      [0, 0, 0, (1 - (1 / np.sqrt(3))), 0, 0],
        #                      [0, 0, 0, 0, 0, 0],
        #                      [0, 0, 0, 0, 0, 0]])

        # Sz = csr_matrix([[1, 0, 0], [0, 0, 0], [0, 0, -1]])
        # yQB = (1 + (1 / np.sqrt(3))) * (Sz * Sz - Sz)
        # zQB = csr_matrix([[1, 0], [0, 1]])
        # print((1 / 2) * scipy.sparse.kron(zQB, yQB).toarray())

        # Spone = (1 / np.sqrt(2)) * csr_matrix([[0, 1, 0], [0, 0, 1], [0, 0, 0]])
        # Sphere =self.a1_dag * self.a2
        # print("Spone ", Spone.toarray())
        # print("Sphere ", Sphere.toarray())
