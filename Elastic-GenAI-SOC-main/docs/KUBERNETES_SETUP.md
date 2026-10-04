# Kubernetes Cluster Setup Guide (3-Node)

This guide walks you through building a **1-Master, 2-Worker** Kubernetes cluster from scratch using `kubeadm`. This is the foundation required to run the Elastic Stack (ECK).

## Prerequisites
*   **3 Virtual Machines (VMs)**:
    *   OS: Ubuntu 22.04 LTS (Recommended)
    *   CPU: 2+ vCPUs per node.
    *   RAM: 4GB+ per node (Elasticsearch is hungry).
    *   Network: Unique hostname, MAC address, and static IP for each node.
*   **Root Privileges**: `sudo` access.

## Step 1: Prepare All Nodes (Run on All 3 Machines)

### 1. Disable Swap
Kubernetes requires swap to be disabled.
```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
```

### 2. Install Container Runtime (containerd)
```bash
# Enable networking modules
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

# Setup required sysctl params
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system

# Install containerd
sudo apt-get update
sudo apt-get install -y containerd

# Retrieve default config and set SystemdCgroup to true
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
sudo systemctl restart containerd
```

### 3. Install kubeadm, kubelet, and kubectl
```bash
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gpg

# Download Google Cloud public signing key
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

# Add Kubernetes apt repository
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

---

## Step 2: Initialize Master Node (Run on Master Only)

Initialize the cluster. Replace `<MASTER_IP>` with your Master Node's static IP.
```bash
sudo kubeadm init --apiserver-advertise-address=<MASTER_IP> --pod-network-cidr=192.168.0.0/16
```
*Note: We use `192.168.0.0/16` for Calico CNI.*

### Configure kubectl for your user
```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### Install Network Plugin (Calico)
```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/tigera-operator.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/custom-resources.yaml
```

---

## Step 3: Join Worker Nodes (Run on Worker 1 & 2)

At the end of the `kubeadm init` command on the master, you received a join command. It looks like this:

```bash
sudo kubeadm join <MASTER_IP>:6443 --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>
```

Run this command on **Worker 1** and **Worker 2**.

---

## Step 4: Verify Cluster

Go back to your **Master Node** and check the status:

```bash
kubectl get nodes
```

You should see 3 nodes with status `Ready`.
Once ready, proceed to [SETUP_GUIDE.md](../SETUP_GUIDE.md) to install the Elastic Stack.
