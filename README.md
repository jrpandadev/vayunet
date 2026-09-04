# VayuNet

> **Federated Environmental Intelligence Platform for Hyper-Local Pollution Detection**

VayuNet is an India-scale environmental intelligence web platform / Progressive Web App (PWA) organized around a single core object — the **Pollution Event** — fusing citizen, sensor, satellite, and weather evidence to detect, forecast, explain, and route hyper-local pollution incidents to relevant authorities.

---

## 🏗 Repository Structure

```text
vayunet/
├── backend/       # API services, ingestion, event processing & routing
├── frontend/      # Citizen reporting PWA & Authority dashboard
├── ml/            # Local predictive models (e.g. XGBoost) & feature pipelines
├── federated/     # Federated learning client/server nodes for cross-city scaling
├── n8n/           # Automated notification, webhook, and authority dispatch workflows
├── data/          # Schemas, sample datasets, and data processing scripts
└── docs/          # Architecture documentation, design docs & specifications
    └── architecture.md  # Master Architecture Specification
```

---

## 📖 Architecture & Documentation

For complete technical specifications, system design, data flows, and Google AI integration details, see:
- [docs/architecture.md](docs/architecture.md)
