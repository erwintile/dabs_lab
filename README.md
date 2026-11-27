# dab_orders_demo

One Databricks Asset Bundle, deployed to 3 targets across 2 Azure Databricks workspaces.
The notebook writes demo orders to `<catalog>.<schema>.orders`.

| Target | Workspace | Deployed by | Schema |
|---|---|---|---|
| `dev` | Dev | Developer, local CLI | `dev.dev_<user>_bronze` |
| `dev_shared` | Dev | GitHub Actions as `sp-dab-dev` (push to `dev`) | `dev.bronze` |
| `prod` | Prod | GitHub Actions as `sp-dab-prod` (push to `main`, after approval) | `prod.bronze` |

Branching: `feature/*` → PR → `dev` → PR + approval → `main`.

## Placeholders

Replace before the first deploy: `<DEV_WORKSPACE_HOST>`, `<PROD_WORKSPACE_HOST>`, `<SP_DAB_DEV_APP_ID>`,
`<SP_DAB_PROD_APP_ID>`, `<DEV_GROUP>` (in `databricks.yml` and `resources/schema.yml`).

## Prerequisites (admin, one-time)

1. Two Unity Catalog–enabled workspaces (dev, prod) attached to the same metastore.
2. Storage credential + external location covering each storage root.
3. Catalogs with storage roots, each bound only to its own workspace:
   ```sql
   CREATE CATALOG dev  MANAGED LOCATION 'abfss://dev@<DEV_STORAGE>.dfs.core.windows.net/';
   CREATE CATALOG prod MANAGED LOCATION 'abfss://prod@<PROD_STORAGE>.dfs.core.windows.net/';
   ```
4. Service principals `sp-dab-dev` (dev workspace) and `sp-dab-prod` (prod workspace), each with workspace access
   and a Databricks OAuth secret.
5. Grants (no human group gets `CREATE SCHEMA` on `prod`):
   ```sql
   GRANT USE CATALOG, CREATE SCHEMA ON CATALOG dev  TO `<SP_DAB_DEV_APP_ID>`;
   GRANT USE CATALOG, CREATE SCHEMA ON CATALOG dev  TO `<DEV_GROUP>`;
   GRANT USE CATALOG, CREATE SCHEMA ON CATALOG prod TO `<SP_DAB_PROD_APP_ID>`;
   ```
6. Serverless jobs compute enabled in both workspaces.
7. Databricks CLI ≥ 0.250 for developers.

## GitHub configuration

Environments (Settings > Environments):

| Environment | Variable `DATABRICKS_HOST` | Secrets `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET` | Required reviewers | Deployment branches |
|---|---|---|---|---|
| `dev` | `<DEV_WORKSPACE_HOST>` | `sp-dab-dev` OAuth | None | `dev` + PRs |
| `prod-validate` | `<PROD_WORKSPACE_HOST>` | `sp-dab-prod` OAuth | None | PRs into `main` |
| `prod` | `<PROD_WORKSPACE_HOST>` | `sp-dab-prod` OAuth | At least 1 | `main` only |

Branch protection:
- `dev`: require PR, 1 approval, status check `validate-dev-shared`.
- `main`: require PR from `dev`, 1 approval, status check `validate-prod`.
- No direct pushes to `dev` or `main`.

Security follow-up: `prod-validate` holds prod SP credentials without an approval gate. For a hardened setup,
use a read-only validation identity or GitHub OIDC workload identity federation.

## Developer workflow

```bash
git clone <repo-url> && cd dab-orders-demo
git checkout dev && git pull
git checkout -b feature/<name>

databricks auth login --host <DEV_WORKSPACE_HOST>   # once, as yourself
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run -t dev ingest_orders_job

git add . && git commit -m "..." && git push -u origin feature/<name>
# open PR feature/<name> -> dev
```

Developers never deploy `dev_shared` or `prod` manually. `bundle destroy` is for `dev` only; never run it against `prod`.

## Fallback without serverless

If serverless jobs are disabled, add a job cluster in `resources/ingest_orders_job.yml`:

```yaml
      job_clusters:
        - job_cluster_key: small
          new_cluster:
            spark_version: 15.4.x-scala2.12
            node_type_id: Standard_D4ds_v5
            num_workers: 1
            data_security_mode: SINGLE_USER
      tasks:
        - task_key: ingest_orders
          job_cluster_key: small
          notebook_task:
            notebook_path: ../src/ingest_orders.py
```
