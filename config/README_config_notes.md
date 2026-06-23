# AI Transcript Intake Config

Generated from Sharepoint_Field_Mapping.xlsx and extended to support the full ADO integration.

## Files

| File | Description |
|---|---|
| `sharepoint_field_mapping.json` | Logical agent field names → SharePoint internal names |
| `choice_values.json` | Allowed SharePoint choice values (used for validation) |
| `mvp_output_schema.json` | Full target JSON schema/defaults for each classified row |
| `extraction_settings.json` | Keyword lists, confidence thresholds, session caps |
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
They also appear as columns AR–AX in `master_opportunities.xlsx`.

## SharePoint field notes

- `UpstreamDownstreamImpact` is the normalized name for the display field `Upsteam/Downstream Impact`.
- `Crosss-Functional/Governance` and `Repositiory/Marketplace Tooling` are preserved exactly as choice values to prevent payload validation failures.
- `Leve 6 - Action/Automation` is preserved exactly from the source file.
- The internal name for Human-In-The-Loop Required appears truncated as `Human_x005F_x002d_In_x005F_x002d_The_x005F_x002d_L`. This is preserved exactly.
