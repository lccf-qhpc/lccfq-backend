import tempfile
from pathlib import Path

from lccfq_backend.model.observables import QPUObservables, QubitObservable
from lccfq_backend.slurm.exporter import export_observables


def test_export_subset_fields():
    obs = QPUObservables(
        qubits={
            0: QubitObservable(
                t1=50.0, t2=30.0, anharmonicity=-0.3, frequency=5.0,
                gate_fidelity_1q=0.995, gate_fidelity_2q=0.97,
                rx_duration=20.0, ry_duration=20.0, sqrt_iswap_duration=40.0,
                reset_duration=200.0, measurement_duration=300.0,
                max_circuit_depth=512
            ),
            1: QubitObservable(
                t1=45.0, t2=28.0, anharmonicity=-0.32, frequency=5.2,
                gate_fidelity_1q=0.994, gate_fidelity_2q=0.965,
                rx_duration=19.0, ry_duration=21.0, sqrt_iswap_duration=42.0,
                reset_duration=210.0, measurement_duration=290.0,
                max_circuit_depth=512
            ),
        }
    )

    with tempfile.NamedTemporaryFile(mode="r+") as f:
        export_observables(obs, Path(f.name), include_all=False, max_qubits=2)
        f.seek(0)
        content = f.read()
        assert "Q0_FREQ=5.0" in content
        assert "Q1_T1=45.0" in content
        assert "Q0_DEPTH=512" in content
        assert "QPU_LAST_UPDATED=" in content


def test_export_all_fields():
    obs = QPUObservables(
        qubits={
            0: QubitObservable(
                t1=51.0, t2=32.0, anharmonicity=-0.29, frequency=5.1,
                gate_fidelity_1q=0.996, gate_fidelity_2q=0.968,
                rx_duration=21.0, ry_duration=19.0, sqrt_iswap_duration=41.0,
                reset_duration=205.0, measurement_duration=295.0,
                max_circuit_depth=256
            )
        }
    )

    with tempfile.NamedTemporaryFile(mode="r+") as f:
        export_observables(obs, Path(f.name), include_all=True)
        f.seek(0)
        content = f.read()
        assert "Q0_T1=51.0" in content
        assert "Q0_ANHARMONICITY=-0.29" in content
        assert "Q0_MEASUREMENT_DURATION=295.0" in content
        assert "QPU_LAST_UPDATED=" in content