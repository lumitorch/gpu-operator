from typing import Optional, TypedDict

import pulumi
from pulumi import ResourceOptions
from pulumi_kubernetes import helm


class GPUOperatorArgs(TypedDict):
    namespace: pulumi.Input[str]
    """The namespace to deploy the operator to."""

    version: pulumi.Input[str]
    """The version of the operator to deploy."""


class GPUOperator(pulumi.ComponentResource):
    def __init__(self,
                 name: str,
                 args: GPUOperatorArgs,
                 opts: Optional[ResourceOptions] = None) -> None:
        super().__init__('gpu-operator-component:index:GPUOperator', name, {}, opts)

        helm.v3.Release(
            "gpu-operator",
            chart="gpu-operator",
            version=args["version"],
            namespace=args["namespace"],
            create_namespace=True,
            repository_opts=helm.v3.RepositoryOptsArgs(
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
                            1010  # DCGM_FI_DEV_PCIE_REPLAY_COUNTER - PCIe replay counter
                        ]
                    }
                },
            },
            opts=pulumi.ResourceOptions(parent=self, provider=opts.provider)
        )

        self.register_outputs({})
