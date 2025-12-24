---
sidebar_position: 1
---

# Welcome to ArgusAI

ArgusAI is an **AI-powered event detection system** for home security. It analyzes video feeds from UniFi Protect cameras, RTSP IP cameras, and USB webcams, detects motion and smart events, and generates natural language descriptions using multi-provider AI.

## What Can ArgusAI Do?

- **Intelligent Event Detection**: Automatically detect and describe what's happening in your camera feeds
- **Multi-Provider AI**: Choose from OpenAI GPT-4, xAI Grok, Anthropic Claude, or Google Gemini
- **Entity Recognition**: Track people, vehicles, and packages across events
- **Smart Notifications**: Push notifications with thumbnails and configurable alert rules
- **Home Integration**: Connect to Home Assistant and Apple HomeKit

## Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/bbengt1/ArgusAI.git
cd ArgusAI

# Copy and configure environment
cp .env.example .env

# Start with Docker Compose
docker-compose up -d
```

Access ArgusAI at `http://localhost:3000`

For production deployments with SSL:
```bash
docker-compose --profile ssl up -d
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/bbengt1/argusai.git
cd argusai

# Run the installation script
./scripts/install.sh
```

## System Requirements

### Docker Deployment
- **Docker Engine**: 20.10 or higher
- **Docker Compose**: V2 or higher
- **Optional**: SSL certificates for HTTPS

### Manual Installation
- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **Database**: SQLite (default) or PostgreSQL
- **Optional**: UniFi Protect controller for native camera integration

## Architecture Overview

```
Camera Capture → Motion Detection → Event Queue → AI Description → Database → Alert Rules → Webhooks/Notifications → WebSocket
```

## Next Steps

- [Docker Deployment](./getting-started/docker-deployment) - Deploy with Docker Compose (recommended)
- [Installation Guide](./getting-started/installation) - Manual installation options
- [Configuration](./getting-started/configuration) - Configure cameras and AI providers
- [Features](./features/ai-analysis) - Learn about all the features
