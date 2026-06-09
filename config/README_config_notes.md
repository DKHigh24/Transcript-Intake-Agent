# AI Transcript Intake Config

Generated from Sharepoint_Field_Mapping.xlsx.

Files:
- sharepoint_field_mapping.json: logical agent field names -> SharePoint internal names
- choice_values.json: allowed SharePoint choice values
- mvp_output_schema.json: target JSON schema/defaults for the classifier output

Notes:
- Your SharePoint file shows 'Upsteam/Downstream Impact' as the display name. The logical field is normalized as 'UpstreamDownstreamImpact'.
- Your SharePoint file shows 'Crosss-Functional/Governance' and 'Repositiory/Marketplace Tooling' exactly as choice values. These are preserved to prevent payload validation failures.
- Your SharePoint file shows 'Leve 6 - Action/Automation' exactly as a choice value. This is preserved to prevent payload validation failures.
- The internal name for Human-In-The-Loop Required appears truncated as 'Human_x005F_x002d_In_x005F_x002d_The_x005F_x002d_L'. This is preserved exactly from the file.
