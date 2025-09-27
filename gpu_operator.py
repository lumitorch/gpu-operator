from typing import Optional, TypedDict

import pulumi
from pulumi import ResourceOptions
import pulumi_kubernetes as kubernetes


class GPUOperatorArgs(TypedDict):
    namespace: Optional[pulumi.Input[str]]
    """The namespace to deploy the operator to. Defaults to `gpu-operator`"""

    version: Optional[pulumi.Input[str]]
    """The version of the operator to deploy. Defaults to `v25.3.4`"""


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

        namespace = args.get("namespace", "gpu-operator")
        version = args.get("version") or "v25.3.4"

        kubernetes.core.v1.ResourceQuota(
            "gpu-operator-quota",
            metadata=kubernetes.meta.v1.ObjectMetaArgs(
                name="gpu-operator-quota",
                namespace="gpu-operator"
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
            opts=pulumi.ResourceOptions(parent=self, provider=opts.provider)
        )

        gpu_driver_daemonset = kubernetes.yaml.ConfigFile(
            "gpu-driver-daemonset",
            file="https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml",
            opts=pulumi.ResourceOptions(parent=self, provider=opts.provider)
        )

        kubernetes.helm.v3.Release(
            "gpu-operator",
            chart="gpu-operator",
            version=version,
            namespace=namespace,
            create_namespace=True,
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
                "dcgmExporter": {
                    "enabled": True,
                    "serviceMonitor": {
                        "enabled": True
                    },
                    "config": {
                        "collectInterval": 1000,  # 1 second - collect metrics frequently
                        "publishInterval": 1000,  # 1 second - publish metrics frequently
                        "fieldIds": [
                            1001,  # DCGM_FI_DEV_GPU_UTIL - GPU utilization percentage
                            1005,  # DCGM_FI_DEV_MEM_COPY_UTIL - Memory utilization
                            1002,  # DCGM_FI_DEV_SM_CLOCK - SM clock frequency
                            1004,  # DCGM_FI_DEV_POWER_USAGE - Power usage
                            1013,  # DCGM_FI_DEV_GPU_TEMP - GPU temperature
                            1018,  # DCGM_FI_DEV_MEMORY_TEMP - Memory temperature
                            1010,  # DCGM_FI_DEV_PCIE_REPLAY_COUNTER - PCIe replay counter
                        ]
                    }
                },
            },
            opts=pulumi.ResourceOptions(parent=self, provider=opts.provider, depends_on=[gpu_driver_daemonset])
        )

        self.register_outputs({})
