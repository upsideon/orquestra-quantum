################################################################################
# © Copyright 2021-2022 Zapata Computing Inc.
################################################################################
import numpy as np
import pytest
import sympy

from orquestra.quantum.circuits import GateOperation, MultiPhaseOperation, split_circuit
from orquestra.quantum.circuits._builtin_gates import (
    CNOT,
    CPHASE,
    CZ,
    ISWAP,
    PHASE,
    RX,
    RY,
    RZ,
    SWAP,
    XX,
    YY,
    ZZ,
    H,
    I,
    T,
    X,
    Y,
    Z,
)
from orquestra.quantum.circuits._circuit import Circuit

RNG = np.random.default_rng(42)

EXAMPLE_OPERATIONS = tuple(
    [
        *[gate(qubit_i) for qubit_i in [0, 1, 4] for gate in [X, Y, Z, H, I, T]],
        *[
            gate(angle)(qubit_i)
            for qubit_i in [0, 1, 4]
            for gate in [PHASE, RX, RY, RZ]
            for angle in [0, 0.1, np.pi / 5, np.pi, 2 * np.pi, sympy.Symbol("theta")]
        ],
        *[
            gate(qubit1_i, qubit2_i)
            for qubit1_i, qubit2_i in [(0, 1), (1, 0), (0, 5), (4, 2)]
            for gate in [CNOT, CZ, SWAP, ISWAP]
        ],
        *[
            gate(angle)(qubit1_i, qubit2_i)
            for qubit1_i, qubit2_i in [(0, 1), (1, 0), (0, 5), (4, 2)]
            for gate in [CPHASE, XX, YY, ZZ]
            for angle in [0, 0.1, np.pi / 5, np.pi, 2 * np.pi, sympy.Symbol("theta")]
        ],
    ]
)


class TestInitialization:
    def test_creating_circuit_has_correct_operations(self):
        circuit = Circuit(operations=EXAMPLE_OPERATIONS)
        assert circuit.operations == list(EXAMPLE_OPERATIONS)

    @pytest.mark.parametrize("n_qubits", [-1.3523, -2])
    def test_creating_circuit_with_negative_n_qubits_fails(self, n_qubits):
        with pytest.raises(ValueError):
            Circuit(n_qubits=n_qubits)

    @pytest.mark.parametrize("n_qubits", [1.3523, 2.292])
    def test_creating_circuit_with_float_n_qubits_fails(self, n_qubits):
        with pytest.raises(ValueError):
            circuit = Circuit(n_qubits=n_qubits)

            assert circuit.n_qubits == int(n_qubits)

    def test_creating_circuit_with_float_integer_passes(self):
        Circuit(n_qubits=5.0)


@pytest.mark.parametrize(
    "circuit",
    [
        Circuit(),
        Circuit([]),
        Circuit([H(0)]),
        Circuit([H(0)], 5),
    ],
)
def test_printing_circuit_doesnt_raise_exception(circuit):
    str(circuit)
    repr(circuit)


class TestConcatenation:
    def test_appending_to_circuit_yields_correct_operations(self):
        circuit = Circuit()
        circuit += H(0)
        circuit += CNOT(0, 2)

        assert circuit.operations == [H(0), CNOT(0, 2)]
        assert circuit.n_qubits == 3

    def test_circuits_sum_yields_correct_operations(self):
        circuit1 = Circuit()
        circuit1 += H(0)
        circuit1 += CNOT(0, 2)

        circuit2 = Circuit([X(2), YY(sympy.Symbol("theta"))(5)])

        res_circuit = circuit1 + circuit2
        assert res_circuit.operations == [
            H(0),
            CNOT(0, 2),
            X(2),
            YY(sympy.Symbol("theta"))(5),
        ]
        assert res_circuit.n_qubits == 6


class TestBindingParams:
    def test_circuit_bound_with_all_params_contains_bound_gates(self):
        theta1, theta2, theta3 = sympy.symbols("theta1:4")
        symbols_map = {theta1: 0.5, theta2: 3.14, theta3: 0}

        circuit = Circuit(
            [
                RX(theta1)(0),
                RY(theta2)(1),
                RZ(theta3)(0),
                RX(theta3)(0),
            ]
        )
        bound_circuit = circuit.bind(symbols_map)

        expected_circuit = Circuit(
            [
                RX(theta1).bind(symbols_map)(0),
                RY(theta2).bind(symbols_map)(1),
                RZ(theta3).bind(symbols_map)(0),
                RX(theta3).bind(symbols_map)(0),
            ]
        )

        assert bound_circuit == expected_circuit

    def test_binding_all_params_leaves_no_free_symbols(self):
        alpha, beta, gamma = sympy.symbols("alpha,beta,gamma")
        circuit = Circuit(
            [
                RX(alpha)(0),
                RY(beta)(1),
                RZ(gamma)(0),
                RX(gamma)(0),
            ]
        )
        bound_circuit = circuit.bind({alpha: 0.5, beta: 3.14, gamma: 0})

        assert not bound_circuit.free_symbols

    def test_binding_some_params_leaves_free_params(self):
        theta1, theta2, theta3 = sympy.symbols("theta1:4")
        circuit = Circuit(
            [
                RX(theta1)(0),
                RY(theta2)(1),
                RZ(theta3)(0),
                RX(theta2)(0),
            ]
        )

        bound_circuit = circuit.bind({theta1: 0.5, theta3: 3.14})
        assert bound_circuit.free_symbols == [theta2]

    def test_binding_excessive_params_binds_only_the_existing_ones(self):
        theta1, theta2, theta3 = sympy.symbols("theta1:4")
        other_param = sympy.symbols("other_param")
        circuit = Circuit(
            [
                RX(theta1)(0),
                RY(theta2)(1),
                RZ(theta3)(0),
                RX(theta2)(0),
            ]
        )

        bound_circuit = circuit.bind({theta1: -np.pi, other_param: 42})
        assert bound_circuit.free_symbols == [theta2, theta3]

    def test_symbols_of_wavefunction_operations_are_present_in_circuits_free_symbols(
        self,
    ):
        alpha, beta = sympy.symbols("alpha, beta")
        circuit = Circuit([RX(alpha)(0), MultiPhaseOperation((beta, 0.5))])

        assert circuit.free_symbols == [alpha, beta]

    def test_binding_symbols_to_circuit_binds_them_to_wavefunction_operation(self):
        alpha, beta = sympy.symbols("alpha, beta")
        circuit = Circuit(
            [RX(alpha)(0), MultiPhaseOperation((beta, 0.5)), RX(beta)(1)]
        ).bind({beta: 0.3})

        assert circuit.free_symbols == [alpha]
        assert circuit.operations == [
            RX(alpha)(0),
            MultiPhaseOperation((0.3, 0.5)),
            RX(0.3)(1),
        ]


def test_splitting_circuits_partitions_it_into_expected_chunks():
    def _predicate(operation):
        return isinstance(operation, GateOperation) and operation.gate.name in (
            "RX",
            "RY",
            "RZ",
        )

    circuit = Circuit(
        [RX(np.pi)(0), RZ(np.pi / 2)(1), CNOT(2, 3), RY(np.pi / 4)(2), X(0), Y(1)]
    )

    expected_partition = [
        (True, Circuit([RX(np.pi)(0), RZ(np.pi / 2)(1)], n_qubits=4)),
        (False, Circuit([CNOT(2, 3)], n_qubits=4)),
        (True, Circuit([RY(np.pi / 4)(2)], n_qubits=4)),
        (False, Circuit([X(0), Y(1)], n_qubits=4)),
    ]

    assert list(split_circuit(circuit, _predicate)) == expected_partition
