# GPU Operator Component

A Pulumi component for deploying and managing the NVIDIA GPU Operator on Kubernetes clusters. This component simplifies the deployment of GPU workloads by automating the installation and configuration of the NVIDIA GPU Operator via Helm.

## Overview

The GPU Operator Component is a Pulumi provider that wraps the NVIDIA GPU Operator Helm chart, providing a declarative way to deploy GPU support to Kubernetes clusters. It handles driver installation, device plugin deployment, and GPU monitoring configuration.

## Features

- **Automated GPU Driver Management**: Configures GPU drivers with custom installation paths
- **Container Device Interface (CDI)**: Enables CDI support for improved container GPU access
- **GPU Monitoring**: Integrated DCGM (Data Center GPU Manager) exporter with Prometheus metrics
- **Flexible Configuration**: Customizable installation directories and monitoring settings
- **Pulumi Integration**: Native Pulumi component with full infrastructure-as-code support

## Installation

### Prerequisites

- Python 3.8 or later
- Pulumi CLI installed
- Access to a Kubernetes cluster with GPU nodes
- `uv` package manager (recommended)

### Install the Component

```bash
# Using uv (recommended)
uv add pulumi-gpu-operator-component

# Using pip
pip install pulumi-gpu-operator-component
```

## Usage

### Basic Usage

```python
import pulumi
from pulumi_gpu_operator_component import GPUOperator, GPUOperatorArgs

# Deploy GPU Operator to the cluster
gpu_operator = GPUOperator(
    "gpu-operator",
    GPUOperatorArgs(
        namespace="gpu-operator",
        version="v25.3.4"
    )
)
```

### Advanced Configuration

The component uses sensible defaults but can be customized through the underlying Helm values:

```python
import pulumi
from pulumi_gpu_operator_component import GPUOperator, GPUOperatorArgs

gpu_operator = GPUOperator(
    "gpu-operator",
    GPUOperatorArgs(
        namespace="gpu-operator-system",
        version="v25.3.4"
    ),
    opts=pulumi.ResourceOptions(
        # Add any additional Pulumi resource options
    )
)
```

## Configuration

### Arguments

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `namespace` | `str` | The Kubernetes namespace to deploy the operator | Yes |
| `version` | `str` | The version of the GPU Operator Helm chart | Yes |

### Default Configuration

The component applies the following default configuration:

- **Driver Installation**: Disabled (assumes pre-installed drivers)
- **Installation Directory**: `/home/kubernetes/bin/nvidia`
- **CDI Support**: Enabled by default
- **DCGM Exporter**: Enabled with ServiceMonitor for Prometheus
- **Monitoring Intervals**: 1 second collection and publish intervals

### Monitoring Metrics

The component automatically configures DCGM to collect the following GPU metrics:

- GPU utilization percentage
- Memory utilization
- SM clock frequency
- Power usage
- GPU temperature
- Memory temperature
- PCIe replay counter

## Development

### Project Structure

```
gpu-operator/
├── README.md              # This file
├── PulumiPlugin.yaml      # Pulumi plugin configuration
├── __main__.py           # Component provider entry point
├── gpu_operator.py       # Main component implementation
└── .gitignore           # Git ignore rules
```

### Setup Development Environment

1. Clone the repository:
```bash
git clone <repository-url>
cd gpu-operator
```

2. Set up the virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
uv sync
```

### Running the Component Provider

To run the component provider locally:

```bash
python __main__.py
```

### Building and Testing

The component can be tested by creating a simple Pulumi program that uses it:

```python
# test_program.py
import pulumi
from gpu_operator import GPUOperator

gpu_op = GPUOperator(
    "test-gpu-operator",
    {
        "namespace": "test-namespace",
        "version": "v25.3.4"
    }
)
```

## Integration Examples

### PyTorch Training Workloads

This component is designed to work with GPU-accelerated workloads such as PyTorch training jobs:

```python
import pulumi
import pulumi_kubernetes as k8s
from pulumi_gpu_operator_component import GPUOperator, GPUOperatorArgs

# Deploy GPU Operator
gpu_operator = GPUOperator(
    "gpu-operator",
    GPUOperatorArgs(
        namespace="gpu-operator",
        version="v25.3.4"
    )
)

# Deploy a PyTorch training job that uses GPUs
pytorch_job = k8s.batch.v1.Job(
    "pytorch-training",
    spec=k8s.batch.v1.JobSpecArgs(
        template=k8s.core.v1.PodTemplateSpecArgs(
            spec=k8s.core.v1.PodSpecArgs(
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="pytorch-trainer",
                        image="pytorch/pytorch:latest",
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            limits={"nvidia.com/gpu": "1"}
                        )
                    )
                ]
            )
        )
    )
)
```

## Troubleshooting

### Common Issues

1. **GPU Nodes Not Ready**: Ensure your Kubernetes cluster has GPU-enabled nodes
2. **Driver Issues**: Verify that GPU drivers are properly installed on nodes
3. **Namespace Permissions**: Ensure the deployment namespace has appropriate RBAC permissions

### Debugging

To debug issues with the GPU Operator deployment:

```bash
# Check GPU Operator pods
kubectl get pods -n gpu-operator

# Check GPU Operator logs
kubectl logs -n gpu-operator -l app=nvidia-gpu-operator

# Verify GPU availability
kubectl describe nodes | grep nvidia.com/gpu
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.

## Acknowledgments

- [NVIDIA GPU Operator](https://github.com/NVIDIA/gpu-operator) for the underlying Kubernetes GPU management
- [Pulumi](https://pulumi.com) for the infrastructure-as-code framework
- The Kubernetes community for GPU device plugin standards
