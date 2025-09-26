from pulumi.provider.experimental import component_provider_host
from gpu_operator import GPUOperator

if __name__ == "__main__":
    component_provider_host(name="gpu-operator-component", components=[GPUOperator])
