# AI Transcript Intake Config

Generated from Sharepoint_Field_Mapping.xlsx and extended to support the full ADO integration.

## Files

| File | Description |
|---|---|
| `sharepoint_field_mapping.json` | Logical agent field names → SharePoint internal names |
| `choice_values.json` | Allowed SharePoint choice values (used for validation) |
| `mvp_output_schema.json` | Full target JSON schema/defaults for each classified row |
| `ado_field_mapping.json` | Documents ADO REST API field paths used by `ado_client.py` (reference only — not read programmatically) |

## Schema notes (mvp_output_schema.json)

The schema now includes **7 ADO tracking fields** at the end of every row. These default to `null` and are populated by the ADO integration:

```json
"ADOWorkItemId":  null,   // integer ADO Issue ID once pushed
"ADOUrl":         null,   // direct browser link to the work item
"ADOStatus":      null,   // "To Do" / "Doing" / "Done" (Basic process) or "New" / "Active" (Agile)
"ADOIteration":   null,   // sprint / iteration path
"ADOAssignedTo":  null,   // display name of the assignee
"ADOLastUpdated": null,   // ISO timestamp of last ADO state change
"ADOPushedAt":    null    // ISO timestamp when this agent first pushed the item
```

These fields are written back to `classified_rows.json` in the archive at push time,
and updated on every subsequent `--mode weekly` run via the Step 0 bulk sync.
They also appear as columns AS–AY in `master_opportunities.xlsx` (with `WeekDate` at AR).

## SharePoint field notes

- `UpstreamDownstreamImpact` is the normalized name for the display field `Upsteam/Downstream Impact`.
- `WorkstreamType` is a lifecycle semantics field (`Transactional`, `Product Vitality`, `Governance`, `Support`, `Unknown`) used for classification/reporting; it is not mapped in `sharepoint_field_mapping.json` unless a SharePoint column is provisioned.
- `Repository/Marketplace Tooling` is the canonical `PrimaryTool` choice value.
- The internal name for Human-In-The-Loop Required appears truncated as `Human_x005F_x002d_In_x005F_x002d_The_x005F_x002d_L`. This is preserved exactly.

## Taxonomy model direction (future enhancement)

Current behavior:
- `ProcessStage` is modeled primarily around transactional flow.
- `SubOrdinateFunction` is currently selected within that framing.

Target behavior:
- `SubOrdinateFunction` should be treated as an orthogonal capability lens that can occur across multiple `WorkstreamType` values and stages.
- Additional stage vocabularies should be introduced per `WorkstreamType` (for example, dedicated stages for Product Vitality).
- A relationship model should connect opportunities across workstreams/stages to expose cross-functional handoffs and dependencies.

Implementation planning for this model is documented in:
- `docs/future-features/workstream-process-relationship-model.md`
- Includes a staged recommendation for `Engineering / Product Vitality` teams that plan by PI and execute by Sprint in Azure DevOps.
