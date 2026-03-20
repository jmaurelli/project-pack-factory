# Delegation Brief

This rendered handoff artifact is derived only from the authoritative `task_record` input. If this brief and the task record differ, the task record is the source of truth.

## task_name

{{ task_record.task_name }}

## operating_root

{{ task_record.operating_root }}

## project_context_reference

{% for reference in task_record.project_context_reference %}
- {{ reference }}
{% endfor %}

## source_spec_reference

{% for reference in task_record.source_spec_reference %}
- {{ reference }}
{% endfor %}

## objective

{{ task_record.objective }}

## files_in_scope

{% for path in task_record.files_in_scope %}
- {{ path }}
{% endfor %}

## required_changes

{% for change in task_record.required_changes %}
- {{ change }}
{% endfor %}

## acceptance_criteria

{% for criterion in task_record.acceptance_criteria %}
- {{ criterion }}
{% endfor %}

## validation_commands

{% for command in task_record.validation_commands %}
- {{ command }}
{% endfor %}

## out_of_scope

{% for item in task_record.out_of_scope %}
- {{ item }}
{% endfor %}

## local_evidence

{% for item in task_record.local_evidence %}
- {{ item }}
{% endfor %}

## task_boundary_rules

{% for rule in task_record.task_boundary_rules %}
- {{ rule }}
{% endfor %}

## required_return_format

{% for item in task_record.required_return_format %}
- {{ item }}
{% endfor %}
