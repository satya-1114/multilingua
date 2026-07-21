# Platform Helm Chart

Deploys the enterprise communication platform: FastAPI backend, Celery worker,
Celery beat scheduler, and the TanStack Start frontend behind an nginx ingress.

## Install

```
kubectl apply -f deploy/k8s/secret.example.yaml  # template — edit first
helm install platform ./deploy/helm \
  --namespace platform --create-namespace \
  --set image.backend.tag=1.2.3 \
  --set image.frontend.tag=1.2.3 \
  --set ingress.host=app.example.com
```

## Upgrade / Rollback

```
helm upgrade platform ./deploy/helm --namespace platform \
  --set image.backend.tag=1.2.4 --set image.frontend.tag=1.2.4
helm rollback platform 1 --namespace platform
```

## Values (highlights)

See `values.yaml` for the full list. Notable keys: `backend.replicaCount`,
`worker.concurrency`, `scheduler.replicaCount`, `ingress.host`,
`existingSecret` (must exist before install).