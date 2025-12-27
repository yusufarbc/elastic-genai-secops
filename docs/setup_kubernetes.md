# Kubernetes (ECK) Setup Guide

This guide covers setting up a Kubernetes cluster from scratch and deploying the Elastic Stack using the ECK Operator.

## Part 1: Cluster Setup (3-Node)
*Skip this part if you already have a Kubernetes cluster.*

### Prerequisites
*   3 VMs (Ubuntu 22.04 LTS).
*   2+ vCPUs, 4GB+ RAM per node.
*   Swap disabled (`sudo swapoff -a`).

### 1.1 Prepare All Nodes
Run on **all nodes**:

1.  **Sysctl Params**:
    ```bash
    cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
    net.bridge.bridge-nf-call-iptables  = 1
    net.ipv4.ip_forward                 = 1
    EOF
    sudo sysctl --system
    ```

2.  **Install Containerd**:
    ```bash
    sudo apt-get update && sudo apt-get install -y containerd
    sudo mkdir -p /etc/containerd
    containerd config default | sudo tee /etc/containerd/config.toml
    sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
    sudo systemctl restart containerd
    ```

3.  **Install Kubeadm/Kubelet**:
    ```bash
    sudo apt-get install -y apt-transport-https ca-certificates curl gpg
    curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
    echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
    sudo apt-get update && sudo apt-get install -y kubelet kubeadm kubectl
    sudo apt-mark hold kubelet kubeadm kubectl
    ```

### 1.2 Initialize Master
Run on **Master** node:
```bash
sudo kubeadm init --pod-network-cidr=192.168.0.0/16
```
Copy the `kubeadm join` command output.

**Configure kubectl**:
```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

**Install Calico Network**:
```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/tigera-operator.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/custom-resources.yaml
```

### 1.3 Join Workers
Run the `kubeadm join` command on **Worker 1 & 2**.

---

## Part 2: Elastic Stack Deployment (ECK)
*Prerequisite: A running K8s cluster.*

### 2.1 Install ECK Operator
```bash
kubectl create -f https://download.elastic.co/downloads/eck/2.11.0/all-in-one.yaml
```

### 2.2 Deploy Components
Apply your manifests (ensure you have the YAML files ready in `infrastructure/kubernetes/`):

1.  **Elasticsearch**: `kubectl apply -f infrastructure/kubernetes/elasticsearch.yaml`
2.  **Kibana**: `kubectl apply -f infrastructure/kubernetes/kibana.yaml`
3.  **Fleet Server**: `kubectl apply -f infrastructure/kubernetes/fleet-server.yaml`

### 2.3 Access & Security

**Get Elastic Password**:
```bash
kubectl get secret quickstart-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d
```

**Access Kibana**:
Find the IP from `kubectl get service`. Login with user `elastic`.

### 2.4 Enroll Agents (Windows)
1.  Go to Fleet in Kibana.
2.  Add Agent -> Windows.
3.  Run the provided command on Windows (use `--insecure` if using self-signed certs).
