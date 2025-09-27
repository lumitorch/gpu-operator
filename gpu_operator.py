from typing import Optional, TypedDict, TypeVar, Any

import pulumi
import pulumi_kubernetes as kubernetes
from pulumi import ResourceOptions

T = TypeVar("T")


# Normalize Input[T] to Output[T] and apply a default when the value is None
# Avoids using Python's `or`, which would clobber valid falsy values like 0 or "".
def with_default(value: Optional[pulumi.Input[T]], default: T) -> pulumi.Output[T]:
    return pulumi.Output.from_input(value).apply(lambda v: default if v is None else v)


def get_gpu_field_ids(gpu_flavor: str) -> list[int]:
    """
    Returns the appropriate DCGM field IDs for the specified GPU flavor.

    Args:
        gpu_flavor: The GPU flavor ('a100', 'l4', 't4')

    Returns:
        List of DCGM field IDs optimized for the GPU flavor
    """
    # Field ID mappings for different GPU flavors
    field_mappings = {
        "a100": [
            1001,  # DCGM_FI_DEV_GPU_UTIL - GPU utilization percentage
            1005,  # DCGM_FI_DEV_MEM_COPY_UTIL - Memory utilization
            1002,  # DCGM_FI_DEV_SM_CLOCK - SM clock frequency
            1004,  # DCGM_FI_DEV_POWER_USAGE - Power usage
            1013,  # DCGM_FI_DEV_GPU_TEMP - GPU temperature
            1018,  # DCGM_FI_DEV_MEMORY_TEMP - Memory temperature
            1010,  # DCGM_FI_DEV_PCIE_REPLAY_COUNTER - PCIe replay counter
        ],
        "l4": [
            1001,  # DCGM_FI_DEV_GPU_UTIL - GPU utilization percentage
            1005,  # DCGM_FI_DEV_MEM_COPY_UTIL - Memory utilization
            1002,  # DCGM_FI_DEV_SM_CLOCK - SM clock frequency
            1004,  # DCGM_FI_DEV_POWER_USAGE - Power usage
            1013,  # DCGM_FI_DEV_GPU_TEMP - GPU temperature
            # L4 GPUs may not support all the same fields as A100
        ],
        "t4": [
            1001,  # DCGM_FI_DEV_GPU_UTIL - GPU utilization percentage
            1005,  # DCGM_FI_DEV_MEM_COPY_UTIL - Memory utilization
            1002,  # DCGM_FI_DEV_SM_CLOCK - SM clock frequency
            1004,  # DCGM_FI_DEV_POWER_USAGE - Power usage
            1013,  # DCGM_FI_DEV_GPU_TEMP - GPU temperature
            # T4 GPUs have a more limited set of supported fields
        ]
    }

    return field_mappings.get(gpu_flavor.lower(), field_mappings["a100"])


# ---- Input validators / coercers -------------------------------------------
# Ensures we always have an Output[int] and fails fast with a helpful message
# if the user passes an invalid value (e.g., "four").

def _coerce_int(x: Any, *, name: str, min_: int | None = None, max_: int | None = None) -> int:
    if isinstance(x, bool):
        raise TypeError(f"{name} must be an integer, not bool")
    if isinstance(x, int):
        n = x
    elif isinstance(x, float) and x.is_integer():
        n = int(x)
    elif isinstance(x, str):
        s = x.strip()
        try:
            n = int(s, 10)
        except ValueError:
            raise TypeError(f"{name} must be an integer (got {x!r})")
    elif x is None:
        raise ValueError(f"{name} is required")
    else:
        raise TypeError(f"{name} must be an integer (got {type(x).__name__})")

    if min_ is not None and n < min_:
        raise ValueError(f"{name} must be ≥ {min_} (got {n})")
    if max_ is not None and n > max_:
        raise ValueError(f"{name} must be ≤ {max_} (got {n})")
    return n


def as_int(value: Optional[pulumi.Input[Any]], *, default: int | None, name: str, min_: int | None = None, max_: int | None = None) -> \
        pulumi.Output[int]:
    # Normalize to Output, apply default if None, then validate/convert to int
    return pulumi.Output.from_input(value).apply(
        lambda v: _coerce_int(default if v is None else v, name=name, min_=min_, max_=max_)
    )


class GPUOperatorArgs(TypedDict):
    namespace: Optional[pulumi.Input[str]]
    """The namespace to deploy the operator to. Defaults to `gpu-operator`"""

    version: Optional[pulumi.Input[str]]
    """The version of the operator to deploy. Defaults to `v25.3.4`"""

    gpu_flavor: Optional[pulumi.Input[str]]
    """The GPU flavor to optimize field IDs for. Supported values: `a100`, `l4`, `t4`. Defaults to `a100`"""


class GPUOperator(pulumi.ComponentResource):
    """
    Manages the deployment of the NVIDIA GPU Operator on Kubernetes clusters using Helm.

    The `GPUOperator` class deploys and configures the NVIDIA GPU Operator to ensure the availability of GPU device drivers and
    GPU-related tools on Kubernetes clusters. It creates a resource quota in the gpu-operator namespace to limit pod creation and
    installs the NVIDIA driver DaemonSet for automatic driver installation on worker nodes with GPUs.
    """

    def __init__(self,
                 name: str,
                 args: GPUOperatorArgs,
                 opts: Optional[ResourceOptions] = None) -> None:
        super().__init__('gpu-operator-component:index:GPUOperator', name, {}, opts)

        # Handle default values with apply for each input
        namespace = with_default(args.get("namespace"), "gpu-operator")
        version = with_default(args.get("version"), "v25.3.4")
        gpu_flavor = with_default(args.get("gpu_flavor"), "a100")

        operator_namespace = kubernetes.core.v1.Namespace(
            "gpu-operator",
            metadata=kubernetes.meta.v1.ObjectMetaArgs(
                name=namespace
            ),
            opts=pulumi.ResourceOptions(parent=self, provider=opts.provider),
        )

        priority_class = kubernetes.core.v1.ResourceQuota(
            "gpu-operator-quota",
            metadata=kubernetes.meta.v1.ObjectMetaArgs(
                name="gpu-operator-quota",
                namespace=namespace
            ),
            spec=kubernetes.core.v1.ResourceQuotaSpecArgs(
                hard={
                    "pods": "100"
                },
                scope_selector=kubernetes.core.v1.ScopeSelectorArgs(
                    match_expressions=[
                        kubernetes.core.v1.ScopedResourceSelectorRequirementArgs(
                            operator="In",
                            scope_name="PriorityClass",
                            values=[
                                "system-node-critical",
                                "system-cluster-critical"
                            ]
                        )
                    ]
                )
            ),
            opts=pulumi.ResourceOptions(parent=self, provider=opts.provider, depends_on=[operator_namespace])
        )

        gpu_driver_daemonset = kubernetes.yaml.v2.ConfigFile(
            "gpu-driver-daemonset",
            file="https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml",
            opts=pulumi.ResourceOptions(parent=self, provider=opts.provider, depends_on=[priority_class])
        )

        kubernetes.helm.v3.Release(
            "gpu-operator",
            chart="gpu-operator",
            version=version,
            namespace=namespace,
            repository_opts=kubernetes.helm.v3.RepositoryOptsArgs(
                repo="https://helm.ngc.nvidia.com/nvidia"
            ),
            values={
                "hostPaths": {
                    "driverInstallDir": "/home/kubernetes/bin/nvidia",
                },
                "toolkit": {
                    "installDir": "/home/kubernetes/bin/nvidia",
                },
                "cdi": {
                    "enabled": True,
                    "default": True
                },
                "driver": {
                    "enabled": False,
                },
                "dcgmExporter": gpu_flavor.apply(lambda flavor: {
                    "enabled": True,
                    "serviceMonitor": {
                        "enabled": True
                    },
                    "config": {
                        "collectInterval": 1000,  # 1 second - collect metrics frequently
                        "publishInterval": 1000,  # 1 second - publish metrics frequently
                        "fieldIds": get_gpu_field_ids(flavor)
                    }
                }),
            },
            opts=pulumi.ResourceOptions(parent=self, provider=opts.provider, depends_on=[operator_namespace, gpu_driver_daemonset])
        )

        self.register_outputs({})
