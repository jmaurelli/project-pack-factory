# Generated Agent README

This generated README is agent-facing runtime orientation only. If this file and the referenced machine-readable artifacts differ, follow the machine-readable artifacts.

## mode

`{{ generated_readme.mode }}`

## start_here

{% for item in generated_readme.start_here %}
- {{ item }}
{% endfor %}

## machine_readable_truth

{% for item in generated_readme.machine_readable_truth %}
- {{ item }}
{% endfor %}

## read_order

{% for item in generated_readme.read_order %}
- {{ item }}
{% endfor %}

## primary_content_files

{% for item in generated_readme.primary_content_files %}
- {{ item }}
{% endfor %}

## validation_status

- result: {{ generated_readme.validation_status.result }}
- summary: {{ generated_readme.validation_status.summary }}
{% for item in generated_readme.validation_status.evidence %}
- evidence: {{ item }}
{% endfor %}

## warning_policy

- default_interpretation: {{ generated_readme.warning_policy.default_interpretation }}
- use_machine_readable_reports_for_detail: {{ generated_readme.warning_policy.use_machine_readable_reports_for_detail }}
{% for item in generated_readme.warning_policy.relevant_warning_classes %}
- relevant_warning_class: {{ item }}
{% endfor %}
