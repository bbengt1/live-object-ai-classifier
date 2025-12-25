#!/bin/bash
# ArgusAI Kubernetes Deployment Script
# Deploys ArgusAI to a Kubernetes cluster under the 'argusai' namespace
#
# Usage:
#   ./scripts/deploy.sh                    # Deploy all resources
#   ./scripts/deploy.sh --dry-run          # Show what would be applied
#   ./scripts/deploy.sh --delete           # Delete all resources
#
# Options:
#   --context CONTEXT    Use specific kubectl context
#   --dry-run            Show what would be applied without applying
#   --delete             Delete all ArgusAI resources
#   --wait               Wait for deployments to be ready
#   --skip-secrets       Skip applying secrets (use existing)
#   --help, -h           Show help message

set -e

# Default values
NAMESPACE="argusai"
DRY_RUN=""
DELETE=false
WAIT=false
SKIP_SECRETS=false
CONTEXT=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
K8S_DIR="$PROJECT_ROOT/k8s"

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy ArgusAI to a Kubernetes cluster"
    echo ""
    echo "Options:"
    echo "  --context CONTEXT    Use specific kubectl context"
    echo "  --dry-run            Show what would be applied without applying"
    echo "  --delete             Delete all ArgusAI resources"
    echo "  --wait               Wait for deployments to be ready"
    echo "  --skip-secrets       Skip applying secrets (use existing)"
    echo "  --help, -h           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Deploy all resources"
    echo "  $0 --dry-run                 # Preview deployment"
    echo "  $0 --context my-cluster      # Deploy to specific cluster"
    echo "  $0 --delete                  # Remove all ArgusAI resources"
    echo "  $0 --wait                    # Deploy and wait for ready"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --context)
            CONTEXT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="--dry-run=client"
            shift
            ;;
        --delete)
            DELETE=true
            shift
            ;;
        --wait)
            WAIT=true
            shift
            ;;
        --skip-secrets)
            SKIP_SECRETS=true
            shift
            ;;
        --help|-h)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Verify kubectl is available
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Set kubectl context if specified
KUBECTL="kubectl"
if [[ -n "$CONTEXT" ]]; then
    KUBECTL="kubectl --context=$CONTEXT"
    log_info "Using kubectl context: $CONTEXT"
fi

# Verify cluster connectivity
if ! $KUBECTL cluster-info &> /dev/null; then
    log_error "Cannot connect to Kubernetes cluster"
    log_error "Make sure your kubeconfig is set up correctly"
    exit 1
fi

# Get current context for confirmation
CURRENT_CONTEXT=$($KUBECTL config current-context)
log_info "Deploying to cluster: $CURRENT_CONTEXT"
log_info "Target namespace: $NAMESPACE"

if [[ -n "$DRY_RUN" ]]; then
    log_warn "DRY RUN MODE - No changes will be made"
fi

echo ""

# Delete mode
if [[ "$DELETE" == "true" ]]; then
    log_warn "Deleting ArgusAI resources from namespace: $NAMESPACE"

    read -p "Are you sure you want to delete all ArgusAI resources? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Aborted"
        exit 0
    fi

    # Delete in reverse order of dependencies
    log_info "Deleting Ingress..."
    $KUBECTL delete -f "$K8S_DIR/ingress.yaml" --ignore-not-found $DRY_RUN || true

    log_info "Deleting Deployments..."
    $KUBECTL delete -f "$K8S_DIR/frontend-deployment.yaml" --ignore-not-found $DRY_RUN || true
    $KUBECTL delete -f "$K8S_DIR/backend-deployment.yaml" --ignore-not-found $DRY_RUN || true

    log_info "Deleting Services..."
    $KUBECTL delete -f "$K8S_DIR/frontend-service.yaml" --ignore-not-found $DRY_RUN || true
    $KUBECTL delete -f "$K8S_DIR/backend-service.yaml" --ignore-not-found $DRY_RUN || true

    log_info "Deleting ConfigMap and Secret..."
    $KUBECTL delete -f "$K8S_DIR/configmap.yaml" --ignore-not-found $DRY_RUN || true
    $KUBECTL delete -f "$K8S_DIR/secret.yaml" --ignore-not-found $DRY_RUN || true

    log_info "Deleting PVC..."
    read -p "Delete PersistentVolumeClaim (DATA WILL BE LOST)? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $KUBECTL delete -f "$K8S_DIR/pvc.yaml" --ignore-not-found $DRY_RUN || true
    else
        log_info "PVC retained"
    fi

    log_info "Deleting Namespace..."
    read -p "Delete the argusai namespace? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $KUBECTL delete -f "$K8S_DIR/namespace.yaml" --ignore-not-found $DRY_RUN || true
    else
        log_info "Namespace retained"
    fi

    log_success "ArgusAI resources deleted"
    exit 0
fi

# Deploy mode
log_info "Starting ArgusAI deployment..."

# Step 1: Create namespace
log_info "Creating namespace..."
$KUBECTL apply -f "$K8S_DIR/namespace.yaml" $DRY_RUN

# Step 2: Apply ConfigMap
log_info "Applying ConfigMap..."
$KUBECTL apply -f "$K8S_DIR/configmap.yaml" $DRY_RUN

# Step 3: Apply Secret (unless skipped)
if [[ "$SKIP_SECRETS" == "false" ]]; then
    log_info "Applying Secret..."

    # Check if secret has empty required values
    if grep -q 'ENCRYPTION_KEY: ""' "$K8S_DIR/secret.yaml"; then
        log_warn "ENCRYPTION_KEY is empty in secret.yaml"
        log_warn "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        log_warn "Then encode with: echo -n 'your-key' | base64"
    fi

    $KUBECTL apply -f "$K8S_DIR/secret.yaml" $DRY_RUN
else
    log_info "Skipping secrets (using existing)"
fi

# Step 4: Apply PVC
log_info "Applying PersistentVolumeClaim..."
$KUBECTL apply -f "$K8S_DIR/pvc.yaml" $DRY_RUN

# Step 5: Apply Services
log_info "Applying Services..."
$KUBECTL apply -f "$K8S_DIR/backend-service.yaml" $DRY_RUN
$KUBECTL apply -f "$K8S_DIR/frontend-service.yaml" $DRY_RUN

# Step 6: Apply Deployments
log_info "Applying Deployments..."
$KUBECTL apply -f "$K8S_DIR/backend-deployment.yaml" $DRY_RUN
$KUBECTL apply -f "$K8S_DIR/frontend-deployment.yaml" $DRY_RUN

# Step 7: Apply Ingress
log_info "Applying Ingress..."
$KUBECTL apply -f "$K8S_DIR/ingress.yaml" $DRY_RUN

# Wait for deployments if requested
if [[ "$WAIT" == "true" && -z "$DRY_RUN" ]]; then
    log_info "Waiting for deployments to be ready..."

    log_info "Waiting for backend deployment..."
    $KUBECTL rollout status deployment/argusai-backend -n $NAMESPACE --timeout=300s

    log_info "Waiting for frontend deployment..."
    $KUBECTL rollout status deployment/argusai-frontend -n $NAMESPACE --timeout=300s

    log_success "All deployments are ready"
fi

echo ""
log_success "ArgusAI deployment complete!"

# Show status
if [[ -z "$DRY_RUN" ]]; then
    echo ""
    log_info "Deployment Status:"
    echo ""
    $KUBECTL get all -n $NAMESPACE

    echo ""
    log_info "To check pod logs:"
    echo "  kubectl logs -f deployment/argusai-backend -n $NAMESPACE"
    echo "  kubectl logs -f deployment/argusai-frontend -n $NAMESPACE"

    echo ""
    log_info "To port-forward for local access:"
    echo "  kubectl port-forward svc/argusai-frontend 3000:3000 -n $NAMESPACE"
    echo "  kubectl port-forward svc/argusai-backend 8000:8000 -n $NAMESPACE"

    # Check ingress
    INGRESS_IP=$($KUBECTL get ingress argusai-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [[ -n "$INGRESS_IP" ]]; then
        echo ""
        log_info "Ingress IP: $INGRESS_IP"
        echo "  Add to /etc/hosts: $INGRESS_IP argusai.local"
    fi
fi
