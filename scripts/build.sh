#!/bin/bash
# ArgusAI Docker Build Script
# Builds Docker containers for backend and/or frontend
#
# Usage:
#   ./scripts/build.sh --frontend     # Build frontend only
#   ./scripts/build.sh --backend      # Build backend only
#   ./scripts/build.sh --both         # Build both containers
#   ./scripts/build.sh                # Defaults to --both
#
# Options:
#   --push          Push images to registry after build
#   --tag TAG       Specify image tag (default: latest)
#   --registry REG  Specify container registry (default: ghcr.io/project-argusai)
#   --no-cache      Build without using cache

set -e

# Default values
REGISTRY="ghcr.io/project-argusai"
TAG="latest"
BUILD_FRONTEND=false
BUILD_BACKEND=false
PUSH=false
NO_CACHE=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build ArgusAI Docker containers"
    echo ""
    echo "Target options (at least one required):"
    echo "  --frontend      Build frontend container"
    echo "  --backend       Build backend container"
    echo "  --both          Build both containers (default if no target specified)"
    echo ""
    echo "Build options:"
    echo "  --push          Push images to registry after build"
    echo "  --tag TAG       Specify image tag (default: latest)"
    echo "  --registry REG  Specify container registry (default: ghcr.io/project-argusai)"
    echo "  --no-cache      Build without using cache"
    echo "  --help, -h      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --frontend                    # Build frontend only"
    echo "  $0 --backend --tag v1.0.0        # Build backend with specific tag"
    echo "  $0 --both --push                 # Build and push both"
    echo "  $0 --frontend --backend          # Same as --both"
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
        --frontend)
            BUILD_FRONTEND=true
            shift
            ;;
        --backend)
            BUILD_BACKEND=true
            shift
            ;;
        --both)
            BUILD_FRONTEND=true
            BUILD_BACKEND=true
            shift
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
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

# Default to building both if no target specified
if [[ "$BUILD_FRONTEND" == "false" && "$BUILD_BACKEND" == "false" ]]; then
    BUILD_FRONTEND=true
    BUILD_BACKEND=true
fi

# Verify Docker is available
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

# Verify Docker daemon is running
if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running"
    exit 1
fi

log_info "Build Configuration:"
echo "  Registry:    $REGISTRY"
echo "  Tag:         $TAG"
echo "  Frontend:    $BUILD_FRONTEND"
echo "  Backend:     $BUILD_BACKEND"
echo "  Push:        $PUSH"
echo "  No Cache:    ${NO_CACHE:-false}"
echo ""

# Build backend
if [[ "$BUILD_BACKEND" == "true" ]]; then
    BACKEND_IMAGE="${REGISTRY}/argusai-backend:${TAG}"
    log_info "Building backend image: $BACKEND_IMAGE"

    cd "$PROJECT_ROOT/backend"

    docker build \
        $NO_CACHE \
        -t "$BACKEND_IMAGE" \
        -f Dockerfile \
        .

    log_success "Backend image built: $BACKEND_IMAGE"

    # Also tag as latest if not already
    if [[ "$TAG" != "latest" ]]; then
        docker tag "$BACKEND_IMAGE" "${REGISTRY}/argusai-backend:latest"
        log_info "Also tagged as: ${REGISTRY}/argusai-backend:latest"
    fi

    if [[ "$PUSH" == "true" ]]; then
        log_info "Pushing backend image..."
        docker push "$BACKEND_IMAGE"
        if [[ "$TAG" != "latest" ]]; then
            docker push "${REGISTRY}/argusai-backend:latest"
        fi
        log_success "Backend image pushed"
    fi
fi

# Build frontend
if [[ "$BUILD_FRONTEND" == "true" ]]; then
    FRONTEND_IMAGE="${REGISTRY}/argusai-frontend:${TAG}"
    log_info "Building frontend image: $FRONTEND_IMAGE"

    cd "$PROJECT_ROOT/frontend"

    # Build with default API URL (will be overridden at runtime via env vars)
    docker build \
        $NO_CACHE \
        --build-arg NEXT_PUBLIC_API_URL=http://argusai-backend:8000 \
        -t "$FRONTEND_IMAGE" \
        -f Dockerfile \
        .

    log_success "Frontend image built: $FRONTEND_IMAGE"

    # Also tag as latest if not already
    if [[ "$TAG" != "latest" ]]; then
        docker tag "$FRONTEND_IMAGE" "${REGISTRY}/argusai-frontend:latest"
        log_info "Also tagged as: ${REGISTRY}/argusai-frontend:latest"
    fi

    if [[ "$PUSH" == "true" ]]; then
        log_info "Pushing frontend image..."
        docker push "$FRONTEND_IMAGE"
        if [[ "$TAG" != "latest" ]]; then
            docker push "${REGISTRY}/argusai-frontend:latest"
        fi
        log_success "Frontend image pushed"
    fi
fi

echo ""
log_success "Build complete!"

# Show image information
echo ""
log_info "Built images:"
if [[ "$BUILD_BACKEND" == "true" ]]; then
    docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep "argusai-backend" | head -2
fi
if [[ "$BUILD_FRONTEND" == "true" ]]; then
    docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep "argusai-frontend" | head -2
fi
